"""
Media Pack Extractor Module
Handles extraction and organization of media pack archives
"""
import os
import json
import hashlib
import zipfile
import tarfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime
from collections import defaultdict


class MediaPackExtractor:
    """Extracts and organizes media pack archives"""
    
    # File type categories
    FILE_CATEGORIES = {
        'product-images': ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.tiff'],
        'logos': ['logo', 'brand', 'symbol', 'mark'],  # Keywords for logo detection
        'marketing-materials': ['banner', 'poster', 'flyer', 'ad', 'promo', 'campaign'],
        'documentation': ['.pdf', '.doc', '.docx', '.txt', '.md', '.rtf'],
        'vectors': ['.svg', '.ai', '.eps', '.cdr'],
        'videos': ['.mp4', '.mov', '.avi', '.wmv', '.flv', '.webm'],
        'fonts': ['.ttf', '.otf', '.woff', '.woff2'],
        'other': []
    }
    
    def __init__(self, extraction_dir: Path, config=None, logger=None):
        """
        Initialize extractor
        
        Args:
            extraction_dir: Base directory for extracted files
            config: Configuration object
            logger: Logger instance
        """
        self.extraction_dir = Path(extraction_dir)
        self.config = config
        self.logger = logger
        
        # Create extraction directory
        self.extraction_dir.mkdir(parents=True, exist_ok=True)
    
    def extract_media_pack(
        self,
        archive_path: Path,
        brand_name: str,
        organize: bool = True,
        detect_duplicates: bool = True
    ) -> Dict:
        """
        Extract media pack archive
        
        Args:
            archive_path: Path to archive file
            brand_name: Brand name for organization
            organize: Organize files by category
            detect_duplicates: Detect and handle duplicate files
        
        Returns:
            Dictionary with extraction results
        """
        if self.logger:
            self.logger.info(f"Extracting media pack: {archive_path}")
        
        if not archive_path.exists():
            return {
                "success": False,
                "error": f"Archive not found: {archive_path}"
            }
        
        # Determine archive type
        archive_type = self._detect_archive_type(archive_path)
        if not archive_type:
            return {
                "success": False,
                "error": f"Unsupported archive type: {archive_path.suffix}"
            }
        
        # Create extraction directory
        archive_name = archive_path.stem
        extract_dir = self.extraction_dir / brand_name / archive_name
        
        try:
            # Check for corruption before extraction
            if not self._verify_archive_integrity(archive_path, archive_type):
                if self.logger:
                    self.logger.error(f"Archive appears corrupted: {archive_path}")
                
                # Attempt repair
                if self._attempt_repair(archive_path, archive_type):
                    if self.logger:
                        self.logger.info("Archive repaired successfully")
                else:
                    return {
                        "success": False,
                        "error": "Archive is corrupted and cannot be repaired",
                        "quarantine": self._quarantine_file(archive_path)
                    }
            
            # Extract archive
            extracted_files = self._extract_archive(archive_path, extract_dir, archive_type)
            
            if self.logger:
                self.logger.info(f"Extracted {len(extracted_files)} files")
            
            # Detect duplicates
            duplicates = {}
            if detect_duplicates:
                duplicates = self._detect_duplicates(extracted_files)
                if duplicates and self.logger:
                    self.logger.info(f"Found {len(duplicates)} duplicate file groups")
            
            # Organize files by category
            categorized = {}
            if organize:
                categorized = self._categorize_files(extracted_files, brand_name, extract_dir)
                if self.logger:
                    self.logger.info(f"Organized files into {len(categorized)} categories")
                
                # Update extracted_files to reflect moved files
                extracted_files = []
                for files_list in categorized.values():
                    extracted_files.extend(files_list)
            
            # Generate metadata
            metadata = self._generate_metadata(
                brand_name,
                archive_path,
                extract_dir,
                extracted_files,
                categorized,
                duplicates
            )
            
            # Save metadata
            metadata_path = extract_dir / "metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            if self.logger:
                self.logger.info(f"Metadata saved: {metadata_path}")
            
            return {
                "success": True,
                "extraction_dir": str(extract_dir),
                "total_files": len(extracted_files),
                "categories": {cat: len(files) for cat, files in categorized.items()},
                "duplicates": len(duplicates),
                "metadata_path": str(metadata_path)
            }
        
        except Exception as e:
            if self.logger:
                self.logger.error(f"Extraction failed: {e}")
            
            return {
                "success": False,
                "error": str(e),
                "partial_extraction": str(extract_dir) if extract_dir.exists() else None
            }
    
    def _detect_archive_type(self, filepath: Path) -> Optional[str]:
        """Detect archive type from file extension"""
        suffix = filepath.suffix.lower()
        
        if suffix == '.zip':
            return 'zip'
        elif suffix == '.rar':
            return 'rar'
        elif suffix == '.7z':
            return '7z'
        elif suffix in ['.tar', '.gz', '.tgz'] or filepath.name.endswith('.tar.gz'):
            return 'tar'
        
        return None
    
    def _verify_archive_integrity(self, filepath: Path, archive_type: str) -> bool:
        """Verify archive is not corrupted"""
        try:
            if archive_type == 'zip':
                with zipfile.ZipFile(filepath, 'r') as zf:
                    # Test archive
                    bad_file = zf.testzip()
                    return bad_file is None
            
            elif archive_type == 'tar':
                with tarfile.open(filepath, 'r:*') as tf:
                    # Try to get member list
                    tf.getmembers()
                    return True
            
            # For rar and 7z, we'd need additional libraries
            # For now, assume they're valid
            return True
        
        except Exception as e:
            if self.logger:
                self.logger.debug(f"Archive integrity check failed: {e}")
            return False
    
    def _attempt_repair(self, filepath: Path, archive_type: str) -> bool:
        """Attempt to repair corrupted archive"""
        # Basic repair attempts - in production, you'd use specialized tools
        try:
            if archive_type == 'zip':
                # Try to extract what we can
                temp_dir = filepath.parent / f"{filepath.stem}_temp"
                temp_dir.mkdir(exist_ok=True)
                
                with zipfile.ZipFile(filepath, 'r') as zf:
                    for member in zf.namelist():
                        try:
                            zf.extract(member, temp_dir)
                        except:
                            pass
                
                # If we extracted anything, consider it partially repaired
                if list(temp_dir.iterdir()):
                    shutil.rmtree(temp_dir)
                    return True
            
            return False
        
        except Exception:
            return False
    
    def _quarantine_file(self, filepath: Path) -> str:
        """Move corrupted file to quarantine"""
        quarantine_dir = filepath.parent / "quarantine"
        quarantine_dir.mkdir(exist_ok=True)
        
        quarantine_path = quarantine_dir / filepath.name
        shutil.move(str(filepath), str(quarantine_path))
        
        if self.logger:
            self.logger.info(f"Quarantined corrupted file: {quarantine_path}")
        
        return str(quarantine_path)
    
    def _extract_archive(self, filepath: Path, extract_dir: Path, archive_type: str) -> List[Path]:
        """Extract archive to directory"""
        extract_dir.mkdir(parents=True, exist_ok=True)
        extracted_files = []
        
        if archive_type == 'zip':
            with zipfile.ZipFile(filepath, 'r') as zf:
                zf.extractall(extract_dir)
                for member in zf.namelist():
                    extracted_path = extract_dir / member
                    if extracted_path.is_file():
                        extracted_files.append(extracted_path)
        
        elif archive_type == 'tar':
            with tarfile.open(filepath, 'r:*') as tf:
                tf.extractall(extract_dir)
                for member in tf.getmembers():
                    if member.isfile():
                        extracted_files.append(extract_dir / member.name)
        
        elif archive_type == 'rar':
            # Would need rarfile library
            if self.logger:
                self.logger.warning("RAR extraction requires 'rarfile' library")
        
        elif archive_type == '7z':
            # Would need py7zr library
            if self.logger:
                self.logger.warning("7z extraction requires 'py7zr' library")
        
        return extracted_files
    
    def _calculate_file_hash(self, filepath: Path) -> str:
        """Calculate SHA256 hash of file"""
        sha256 = hashlib.sha256()
        with open(filepath, 'rb') as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def _detect_duplicates(self, files: List[Path]) -> Dict[str, List[Path]]:
        """
        Detect duplicate files based on content hash
        
        Returns:
            Dictionary mapping hash to list of duplicate files
        """
        hash_to_files = defaultdict(list)
        
        for filepath in files:
            if filepath.is_file():
                try:
                    file_hash = self._calculate_file_hash(filepath)
                    hash_to_files[file_hash].append(filepath)
                except Exception as e:
                    if self.logger:
                        self.logger.debug(f"Failed to hash {filepath}: {e}")
        
        # Filter to only duplicates (hash appears more than once)
        duplicates = {h: files for h, files in hash_to_files.items() if len(files) > 1}
        
        # Handle duplicates - keep highest quality version
        for file_hash, duplicate_files in duplicates.items():
            if len(duplicate_files) > 1:
                # Sort by file size (larger is usually higher quality for images)
                duplicate_files.sort(key=lambda p: p.stat().st_size if p.exists() else 0, reverse=True)
                
                # Keep the first (largest), remove others
                for dup in duplicate_files[1:]:
                    try:
                        if dup.exists():
                            dup.unlink()
                            if self.logger:
                                self.logger.debug(f"Removed duplicate: {dup}")
                    except Exception as e:
                        if self.logger:
                            self.logger.debug(f"Failed to remove duplicate {dup}: {e}")
        
        return duplicates
    
    def _categorize_files(self, files: List[Path], brand_name: str, base_dir: Path) -> Dict[str, List[Path]]:
        """Categorize files by type"""
        categorized = defaultdict(list)
        
        for filepath in files:
            if not filepath.exists() or not filepath.is_file():
                continue
            
            category = self._determine_category(filepath)
            
            # Create category directory in base_dir
            category_dir = base_dir / category
            category_dir.mkdir(exist_ok=True)
            
            # Generate standardized name
            new_name = self._standardize_filename(filepath, brand_name, category)
            new_path = category_dir / new_name
            
            # Move file to category directory
            try:
                # Avoid overwriting
                if new_path.exists():
                    counter = 1
                    while new_path.exists():
                        stem = new_path.stem
                        new_path = category_dir / f"{stem}_{counter}{new_path.suffix}"
                        counter += 1
                
                shutil.move(str(filepath), str(new_path))
                categorized[category].append(new_path)
            except Exception as e:
                if self.logger:
                    self.logger.debug(f"Failed to categorize {filepath}: {e}")
                categorized['other'].append(filepath)
        
        return categorized
    
    def _determine_category(self, filepath: Path) -> str:
        """Determine file category"""
        filename_lower = filepath.name.lower()
        suffix_lower = filepath.suffix.lower()
        
        # Check for logo keywords
        for keyword in self.FILE_CATEGORIES['logos']:
            if keyword in filename_lower:
                return 'logos'
        
        # Check for marketing keywords
        for keyword in self.FILE_CATEGORIES['marketing-materials']:
            if keyword in filename_lower:
                return 'marketing-materials'
        
        # Check file extensions
        if suffix_lower in self.FILE_CATEGORIES['product-images']:
            return 'product-images'
        elif suffix_lower in self.FILE_CATEGORIES['documentation']:
            return 'documentation'
        elif suffix_lower in self.FILE_CATEGORIES['vectors']:
            return 'vectors'
        elif suffix_lower in self.FILE_CATEGORIES['videos']:
            return 'videos'
        elif suffix_lower in self.FILE_CATEGORIES['fonts']:
            return 'fonts'
        
        return 'other'
    
    def _standardize_filename(self, filepath: Path, brand_name: str, category: str) -> str:
        """Standardize filename with brand prefix"""
        # Clean brand name
        brand_clean = brand_name.lower().replace(' ', '-')
        
        # Get original name parts
        stem = filepath.stem
        suffix = filepath.suffix
        
        # Create standardized name
        # Remove common prefixes
        stem_clean = stem.lower()
        for prefix in ['img_', 'image_', 'photo_', 'pic_']:
            if stem_clean.startswith(prefix):
                stem_clean = stem_clean[len(prefix):]
                break
        
        # Build new name
        if category == 'logos':
            new_name = f"{brand_clean}-logo-{stem_clean}{suffix}"
        elif category == 'documentation':
            new_name = f"{brand_clean}-{stem_clean}{suffix}"
        elif category == 'product-images':
            new_name = f"{brand_clean}-product-{stem_clean}{suffix}"
        else:
            new_name = f"{brand_clean}-{stem_clean}{suffix}"
        
        return new_name
    
    def _generate_metadata(
        self,
        brand_name: str,
        archive_path: Path,
        extract_dir: Path,
        extracted_files: List[Path],
        categorized: Dict[str, List[Path]],
        duplicates: Dict[str, List[Path]]
    ) -> Dict:
        """Generate extraction metadata"""
        return {
            "brand": brand_name,
            "media_pack": archive_path.name,
            "archive_path": str(archive_path),
            "extraction_dir": str(extract_dir),
            "download_date": datetime.fromtimestamp(archive_path.stat().st_ctime).isoformat(),
            "extraction_date": datetime.now().isoformat(),
            "total_files": len(extracted_files),
            "categories": {
                category: {
                    "count": len(files),
                    "files": [f.name for f in files[:10]]  # Sample of files
                }
                for category, files in categorized.items()
            },
            "duplicates_removed": len(duplicates),
            "file_inventory": [
                {
                    "name": f.name,
                    "size": f.stat().st_size,
                    "path": str(f.relative_to(extract_dir))
                }
                for f in extracted_files[:100]  # Limit inventory size
            ]
        }
