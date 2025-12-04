from typing import List
import fnmatch
import os
class FileCollector:
    def collect(self, base_directory: str, patterns: List[str]) -> List[str]:
        if not os.path.isdir(base_directory):
            raise FileNotFoundError

        result = []

        for root, dirs, files in os.walk(base_directory):
            for fname in files:
                for pattern in patterns:
                    if fnmatch.fnmatch(fname, pattern):
                        file_path = os.path.join(root, fname)
                        if os.path.isfile(file_path):
                            result.append(file_path)
        return result
