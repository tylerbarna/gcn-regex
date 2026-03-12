import os
import tarfile
import json
import argparse

def pack_archive(archive_folder, tarballs_folder, max_size_mb=20, overwrite=True):
    if not os.path.exists(tarballs_folder):
        os.makedirs(tarballs_folder)

    tarball_index = 1
    current_tarball_size = 0
    current_tarball_files = []
    
    for filename in os.listdir(archive_folder):
        if filename.endswith('.json'):
            file_path = os.path.join(archive_folder, filename)
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            
            if current_tarball_size + file_size_mb > max_size_mb:
                tarball_name = f'archive_{tarball_index}.tar.gz'
                tarball_path = os.path.join(tarballs_folder, tarball_name)
                with tarfile.open(tarball_path, 'w:gz') as tar:
                    for f in current_tarball_files:
                        tar.add(f, arcname=os.path.basename(f))
                
                print(f'Created {tarball_name} with size {current_tarball_size:.2f} MB')
                tarball_index += 1
                current_tarball_size = 0
                current_tarball_files = []
            
            current_tarball_files.append(file_path)
            current_tarball_size += file_size_mb

    if current_tarball_files:
        tarball_name = f'archive_{tarball_index}.tar.gz'
        tarball_path = os.path.join(tarballs_folder, tarball_name)
        
        if os.path.exists(tarball_path) and not overwrite:
            raise FileExistsError(f'{tarball_name} already exists. Use --overwrite to replace it.')
        
        with tarfile.open(tarball_path, 'w:gz') as tar:
            for f in current_tarball_files:
                tar.add(f, arcname=os.path.basename(f))
        
        print(f'Created {tarball_name} with size {current_tarball_size:.2f} MB')
        
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Pack JSON files from archive folder into tarballs')
    parser.add_argument('--archive_folder', default='./archive', help='Path to the archive folder containing JSON files')
    parser.add_argument('--tarballs_folder', default='./tarballs', help='Path to save tarballs (default: ./tarballs)')
    parser.add_argument('--overwrite', action='store_false', help='Overwrite existing tarballs if they exist')
    parser.add_argument('--max_size_mb', type=int, default=20, help='Maximum size of each tarball in MB (default: 20)')
    
    args = parser.parse_args()
    archive_folder = args.archive_folder
    tarballs_folder = args.tarballs_folder
    overwrite = args.overwrite
    max_size_mb = args.max_size_mb
    pack_archive(archive_folder, tarballs_folder, max_size_mb=max_size_mb, overwrite=overwrite)