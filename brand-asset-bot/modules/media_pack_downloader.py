"""
Media Pack Downloader Module
Handles downloading media packs with progress tracking, resumable downloads, and integrity verification
"""
import os
import hashlib
import time
from pathlib import Path
from typing import Optional, Callable, Dict
import requests
from requests.exceptions import RequestException


class DownloadProgress:
    """Track download progress"""
    
    def __init__(self, total_size: int, brand_name: str, filename: str):
        self.total_size = total_size
        self.downloaded = 0
        self.brand_name = brand_name
        self.filename = filename
        self.start_time = time.time()
        self.last_update_time = time.time()
    
    def update(self, chunk_size: int):
        """Update progress"""
        self.downloaded += chunk_size
        self.last_update_time = time.time()
    
    def get_progress_percent(self) -> float:
        """Get progress percentage"""
        if self.total_size == 0:
            return 0.0
        return (self.downloaded / self.total_size) * 100
    
    def get_speed(self) -> float:
        """Get download speed in bytes per second"""
        elapsed = time.time() - self.start_time
        if elapsed == 0:
            return 0.0
        return self.downloaded / elapsed
    
    def get_eta(self) -> float:
        """Get estimated time remaining in seconds"""
        speed = self.get_speed()
        if speed == 0:
            return 0.0
        remaining = self.total_size - self.downloaded
        return remaining / speed
    
    def format_size(self, size: int) -> str:
        """Format size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    def format_time(self, seconds: float) -> str:
        """Format time in human-readable format"""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            return f"{seconds/60:.0f}m {seconds%60:.0f}s"
        else:
            hours = seconds / 3600
            minutes = (seconds % 3600) / 60
            return f"{hours:.0f}h {minutes:.0f}m"


class MediaPackDownloader:
    """Downloads media packs with progress tracking and resume support"""
    
    def __init__(self, download_dir: Path, config=None, logger=None):
        """
        Initialize downloader
        
        Args:
            download_dir: Base directory for downloads
            config: Configuration object
            logger: Logger instance
        """
        self.download_dir = Path(download_dir)
        self.config = config
        self.logger = logger
        self.session = requests.Session()
        
        # Create download directory
        self.download_dir.mkdir(parents=True, exist_ok=True)
    
    def download_media_pack(
        self,
        url: str,
        brand_name: str,
        filename: Optional[str] = None,
        resume: bool = True,
        verify_integrity: bool = True,
        progress_callback: Optional[Callable[[DownloadProgress], None]] = None
    ) -> Dict:
        """
        Download a media pack
        
        Args:
            url: URL to download
            brand_name: Brand name for directory organization
            filename: Optional filename override
            resume: Enable resumable downloads
            verify_integrity: Verify file integrity after download
            progress_callback: Optional callback for progress updates
        
        Returns:
            Dictionary with download results
        """
        if self.logger:
            self.logger.info(f"Downloading media pack for {brand_name}: {url}")
        
        # Handle Dropbox shared links - convert to direct download
        if 'dropbox.com' in url and 'dl=0' in url:
            url = url.replace('dl=0', 'dl=1')
            if self.logger:
                self.logger.info(f"Converted Dropbox link to direct download: {url}")
        
        # Create brand-specific directory
        brand_dir = self.download_dir / brand_name / "media-packs"
        brand_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine filename
        if not filename:
            filename = self._extract_filename_from_url(url)
        
        filepath = brand_dir / filename
        
        # Check if file already exists and is complete
        if filepath.exists() and not resume:
            if self.logger:
                self.logger.info(f"File already exists: {filepath}")
            return {
                "success": True,
                "filepath": str(filepath),
                "size": filepath.stat().st_size,
                "already_existed": True
            }
        
        # Get file info
        try:
            head_response = self.session.head(url, allow_redirects=True, timeout=30)
            total_size = int(head_response.headers.get('content-length', 0))
            supports_resume = 'accept-ranges' in head_response.headers
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to get file info: {e}")
            return {
                "success": False,
                "error": f"Failed to get file info: {e}"
            }
        
        # Check for partial download
        start_byte = 0
        if resume and filepath.exists() and supports_resume:
            start_byte = filepath.stat().st_size
            if start_byte >= total_size:
                if self.logger:
                    self.logger.info(f"File already complete: {filepath}")
                return {
                    "success": True,
                    "filepath": str(filepath),
                    "size": total_size,
                    "resumed": False,
                    "already_existed": True
                }
        
        # Download file
        try:
            start_time = time.time()
            
            # Set up headers for resume
            headers = {}
            if start_byte > 0:
                headers['Range'] = f'bytes={start_byte}-'
                if self.logger:
                    self.logger.info(f"Resuming download from byte {start_byte}")
            
            # Start download
            response = self.session.get(
                url,
                headers=headers,
                stream=True,
                timeout=30
            )
            response.raise_for_status()
            
            # Open file for writing (append if resuming)
            mode = 'ab' if start_byte > 0 else 'wb'
            
            # Create progress tracker
            progress = DownloadProgress(total_size, brand_name, filename)
            progress.downloaded = start_byte
            
            # Download with progress
            chunk_size = 8192
            with open(filepath, mode) as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        progress.update(len(chunk))
                        
                        # Call progress callback
                        if progress_callback:
                            progress_callback(progress)
                        
                        # Log progress periodically
                        if self.logger and (time.time() - progress.last_update_time > 5):
                            percent = progress.get_progress_percent()
                            speed = progress.format_size(progress.get_speed())
                            self.logger.debug(
                                f"Progress: {percent:.1f}% - {speed}/s"
                            )
            
            download_time = time.time() - start_time
            
            if self.logger:
                self.logger.info(
                    f"Download complete: {filepath} "
                    f"({progress.format_size(total_size)} in {progress.format_time(download_time)})"
                )
            
            # Verify integrity if requested
            checksum = None
            if verify_integrity:
                checksum = self._calculate_checksum(filepath)
                if self.logger:
                    self.logger.info(f"File checksum (SHA256): {checksum}")
            
            return {
                "success": True,
                "filepath": str(filepath),
                "size": total_size,
                "download_time": download_time,
                "resumed": start_byte > 0,
                "checksum": checksum
            }
        
        except Exception as e:
            if self.logger:
                self.logger.error(f"Download failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "partial_file": str(filepath) if filepath.exists() else None
            }
    
    def _extract_filename_from_url(self, url: str) -> str:
        """Extract filename from URL"""
        from urllib.parse import urlparse, unquote
        
        parsed = urlparse(url)
        filename = os.path.basename(parsed.path)
        
        if not filename or '.' not in filename:
            filename = "media-pack.zip"
        
        return unquote(filename)
    
    def _calculate_checksum(self, filepath: Path, algorithm: str = 'sha256') -> str:
        """
        Calculate file checksum
        
        Args:
            filepath: Path to file
            algorithm: Hash algorithm (sha256, md5, etc.)
        
        Returns:
            Hex digest of checksum
        """
        hash_obj = hashlib.new(algorithm)
        
        with open(filepath, 'rb') as f:
            while chunk := f.read(8192):
                hash_obj.update(chunk)
        
        return hash_obj.hexdigest()
    
    def verify_file_integrity(
        self,
        filepath: Path,
        expected_checksum: Optional[str] = None,
        algorithm: str = 'sha256'
    ) -> bool:
        """
        Verify file integrity
        
        Args:
            filepath: Path to file
            expected_checksum: Expected checksum (if known)
            algorithm: Hash algorithm
        
        Returns:
            True if file is valid
        """
        if not filepath.exists():
            return False
        
        actual_checksum = self._calculate_checksum(filepath, algorithm)
        
        if expected_checksum:
            return actual_checksum == expected_checksum
        
        # If no expected checksum, just verify file is readable
        return True
    
    def get_download_info(self, url: str) -> Dict:
        """
        Get information about a downloadable file
        
        Args:
            url: URL to check
        
        Returns:
            Dictionary with file information
        """
        try:
            response = self.session.head(url, allow_redirects=True, timeout=30)
            
            return {
                "url": url,
                "size": int(response.headers.get('content-length', 0)),
                "content_type": response.headers.get('content-type', ''),
                "supports_resume": 'accept-ranges' in response.headers,
                "accessible": response.status_code == 200,
                "filename": self._extract_filename_from_url(url)
            }
        
        except Exception as e:
            return {
                "url": url,
                "accessible": False,
                "error": str(e)
            }
    
    def cleanup_partial_downloads(self, brand_name: Optional[str] = None):
        """
        Clean up partial downloads
        
        Args:
            brand_name: Optional brand name to filter cleanup
        """
        if brand_name:
            brand_dir = self.download_dir / brand_name / "media-packs"
            if brand_dir.exists():
                self._cleanup_directory(brand_dir)
        else:
            # Clean all brand directories
            for brand_dir in self.download_dir.iterdir():
                if brand_dir.is_dir():
                    media_dir = brand_dir / "media-packs"
                    if media_dir.exists():
                        self._cleanup_directory(media_dir)
    
    def _cleanup_directory(self, directory: Path):
        """Clean up partial files in directory"""
        for filepath in directory.glob("*.part"):
            try:
                filepath.unlink()
                if self.logger:
                    self.logger.info(f"Removed partial file: {filepath}")
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Failed to remove {filepath}: {e}")
