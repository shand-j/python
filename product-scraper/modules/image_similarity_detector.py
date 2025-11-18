"""
Image similarity detection module using perceptual hashing.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import hashlib


@dataclass
class ImageHash:
    """Perceptual hash of an image"""
    image_path: str
    hash_value: str  # Hex string representation
    hash_bits: int  # Number of bits in hash
    source: str


@dataclass
class SimilarityMatch:
    """Similarity match between two images"""
    image_1: str
    image_2: str
    source_1: str
    source_2: str
    similarity_score: float  # 0.0-1.0
    hamming_distance: int
    is_duplicate: bool


class ImageSimilarityDetector:
    """Detects similar and duplicate images using perceptual hashing"""
    
    def __init__(self, hash_size: int = 8, similarity_threshold: float = 0.90):
        """
        Initialize detector.
        
        Args:
            hash_size: Size of perceptual hash (8 = 64 bits, 16 = 256 bits)
            similarity_threshold: Threshold for considering images as duplicates (0.0-1.0)
        """
        self.hash_size = hash_size
        self.hash_bits = hash_size * hash_size
        self.similarity_threshold = similarity_threshold
        self.max_hamming_distance = int(self.hash_bits * (1 - similarity_threshold))
    
    def compute_image_hash(self, image_path: str, source: str) -> ImageHash:
        """
        Compute perceptual hash for an image.
        
        In a real implementation, this would:
        1. Load the image
        2. Resize to hash_size x hash_size
        3. Convert to grayscale
        4. Compute DCT (Discrete Cosine Transform)
        5. Keep low-frequency components
        6. Create binary hash based on median
        
        For this implementation, we'll simulate with a simple hash.
        
        Args:
            image_path: Path to image file
            source: Source name
            
        Returns:
            ImageHash object
        """
        # Simulate perceptual hash (in real implementation, would use PIL/imagehash library)
        # This is a placeholder that creates deterministic hashes based on path
        hash_bytes = hashlib.sha256(image_path.encode()).digest()
        
        # Take first hash_bits bits
        num_bytes = (self.hash_bits + 7) // 8
        hash_value = hash_bytes[:num_bytes].hex()
        
        return ImageHash(
            image_path=image_path,
            hash_value=hash_value,
            hash_bits=self.hash_bits,
            source=source
        )
    
    def calculate_hamming_distance(self, hash_1: ImageHash, hash_2: ImageHash) -> int:
        """
        Calculate Hamming distance between two image hashes.
        
        Args:
            hash_1: First image hash
            hash_2: Second image hash
            
        Returns:
            Hamming distance (number of differing bits)
        """
        if hash_1.hash_bits != hash_2.hash_bits:
            raise ValueError("Hash sizes must match")
        
        # Convert hex strings to integers
        int_1 = int(hash_1.hash_value, 16)
        int_2 = int(hash_2.hash_value, 16)
        
        # XOR and count set bits
        xor_result = int_1 ^ int_2
        
        # Count number of 1 bits
        distance = bin(xor_result).count('1')
        
        return distance
    
    def calculate_similarity(self, hash_1: ImageHash, hash_2: ImageHash) -> float:
        """
        Calculate similarity score between two image hashes.
        
        Args:
            hash_1: First image hash
            hash_2: Second image hash
            
        Returns:
            Similarity score (0.0 = completely different, 1.0 = identical)
        """
        distance = self.calculate_hamming_distance(hash_1, hash_2)
        
        # Convert distance to similarity score
        similarity = 1.0 - (distance / hash_1.hash_bits)
        
        return similarity
    
    def find_similar_images(self, hashes: List[ImageHash]) -> List[SimilarityMatch]:
        """
        Find similar images in a list of hashes.
        
        Args:
            hashes: List of ImageHash objects
            
        Returns:
            List of SimilarityMatch objects
        """
        matches = []
        
        # Compare each pair of hashes
        for i, hash_1 in enumerate(hashes):
            for hash_2 in hashes[i+1:]:
                distance = self.calculate_hamming_distance(hash_1, hash_2)
                similarity = 1.0 - (distance / hash_1.hash_bits)
                
                # Only include if above a minimum similarity
                if similarity >= 0.70:  # Minimum 70% similarity
                    matches.append(SimilarityMatch(
                        image_1=hash_1.image_path,
                        image_2=hash_2.image_path,
                        source_1=hash_1.source,
                        source_2=hash_2.source,
                        similarity_score=similarity,
                        hamming_distance=distance,
                        is_duplicate=similarity >= self.similarity_threshold
                    ))
        
        # Sort by similarity (highest first)
        matches.sort(key=lambda m: m.similarity_score, reverse=True)
        
        return matches
    
    def find_duplicates(self, hashes: List[ImageHash]) -> Dict[str, List[str]]:
        """
        Group duplicate images.
        
        Args:
            hashes: List of ImageHash objects
            
        Returns:
            Dict mapping representative image paths to lists of duplicate paths
        """
        duplicates = {}
        processed = set()
        
        for i, hash_1 in enumerate(hashes):
            if hash_1.image_path in processed:
                continue
            
            # Find all duplicates of this image
            group = [hash_1.image_path]
            
            for hash_2 in hashes[i+1:]:
                if hash_2.image_path in processed:
                    continue
                
                distance = self.calculate_hamming_distance(hash_1, hash_2)
                if distance <= self.max_hamming_distance:
                    group.append(hash_2.image_path)
                    processed.add(hash_2.image_path)
            
            if len(group) > 1:
                duplicates[hash_1.image_path] = group[1:]
            
            processed.add(hash_1.image_path)
        
        return duplicates
    
    def detect_near_duplicates(self, images_by_source: Dict[str, List[str]], 
                              similarity_threshold: Optional[float] = None) -> List[SimilarityMatch]:
        """
        Detect near-duplicate images across different sources.
        
        Args:
            images_by_source: Dict mapping source names to lists of image paths
            similarity_threshold: Override default threshold
            
        Returns:
            List of SimilarityMatch objects for cross-source duplicates
        """
        if similarity_threshold:
            old_threshold = self.similarity_threshold
            self.similarity_threshold = similarity_threshold
            self.max_hamming_distance = int(self.hash_bits * (1 - similarity_threshold))
        
        # Compute hashes for all images
        all_hashes = []
        for source, images in images_by_source.items():
            for image_path in images:
                hash_obj = self.compute_image_hash(image_path, source)
                all_hashes.append(hash_obj)
        
        # Find matches
        matches = self.find_similar_images(all_hashes)
        
        # Filter for cross-source matches only
        cross_source_matches = [
            m for m in matches 
            if m.source_1 != m.source_2 and m.is_duplicate
        ]
        
        # Restore original threshold
        if similarity_threshold:
            self.similarity_threshold = old_threshold
            self.max_hamming_distance = int(self.hash_bits * (1 - old_threshold))
        
        return cross_source_matches
    
    def generate_similarity_report(self, matches: List[SimilarityMatch]) -> Dict:
        """Generate report of similarity detection results"""
        total_matches = len(matches)
        duplicates = [m for m in matches if m.is_duplicate]
        near_duplicates = [m for m in matches if not m.is_duplicate]
        
        # Group by source pairs
        source_pairs = {}
        for match in duplicates:
            pair_key = tuple(sorted([match.source_1, match.source_2]))
            if pair_key not in source_pairs:
                source_pairs[pair_key] = 0
            source_pairs[pair_key] += 1
        
        # Calculate average similarity
        avg_similarity = (
            sum(m.similarity_score for m in matches) / total_matches 
            if total_matches > 0 else 0.0
        )
        
        return {
            'summary': {
                'total_matches': total_matches,
                'exact_duplicates': len([m for m in duplicates if m.similarity_score >= 0.99]),
                'near_duplicates': len(duplicates),
                'similar_images': len(near_duplicates),
                'average_similarity': f"{avg_similarity:.3f}"
            },
            'cross_source_duplicates': source_pairs,
            'similarity_distribution': {
                '0.95-1.00': len([m for m in matches if m.similarity_score >= 0.95]),
                '0.90-0.95': len([m for m in matches if 0.90 <= m.similarity_score < 0.95]),
                '0.80-0.90': len([m for m in matches if 0.80 <= m.similarity_score < 0.90]),
                '0.70-0.80': len([m for m in matches if 0.70 <= m.similarity_score < 0.80])
            }
        }
