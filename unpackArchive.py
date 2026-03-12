import os
import tarfile
import argparse

def resolve_tarball_paths(tarball_path):
    if os.path.isfile(tarball_path):
        return [tarball_path]

    if not os.path.isdir(tarball_path):
        raise FileNotFoundError(f'Tarball path does not exist: {tarball_path}')

    tarball_paths = sorted(
        os.path.join(tarball_path, filename)
        for filename in os.listdir(tarball_path)
        if filename.endswith(('.tar.gz', '.tgz'))
    )
    if tarball_paths:
        return tarball_paths

    raise FileNotFoundError(f'No tarballs found in {tarball_path}')


def unpack_archive(tarball_path, output_folder):
    os.makedirs(output_folder, exist_ok=True)

    total_size_bytes = 0
    num_files = 0

    for tarball_file in resolve_tarball_paths(tarball_path):
        with tarfile.open(tarball_file, 'r:gz') as tar:
            json_members = [
                member for member in tar.getmembers()
                if member.isfile() and member.name.endswith('.json')
            ]
            tar.extractall(path=output_folder)
        num_files += len(json_members)
        total_size_bytes += sum(member.size for member in json_members)

    total_size_mb = total_size_bytes / (1024 * 1024)
    
    print(f'Unpacked {num_files} files with total size {total_size_mb:.2f} MB')
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Unpack a tarball into an archive folder')
    parser.add_argument('--tarball_path', '-p', default='./tarballs', help='Path to the tarball to unpack')
    parser.add_argument('--output_folder', '-o', default='./archive', help='Path to save unpacked files (default: ./archive)')
    
    args = parser.parse_args()
    unpack_archive(args.tarball_path, args.output_folder)