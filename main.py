"""Opens images and organizes them into separate folders based on the metadata.

"""
import argparse
import os
import shutil
import datetime
import pathlib
import glob
from PIL import Image
from PIL.ExifTags import TAGS


def find_images(directory, image_ext='jpg'):
    """ Returns a list of images at the input directory and subdirectories. """

    return_images = list()
    pattern = f'*.{image_ext}'
    print(f'Looking for images in {directory} with extension {image_ext}')
    # First check the parent directory for any files
    new_files = glob.glob(os.path.join(directory, pattern))
    return_images.extend(new_files)
    # Do the same thing with any subdirectories
    for dirName, subdirList, fileList in os.walk(directory):
        if len(subdirList) > 0:
            for subdir in subdirList:
                updated_files = find_images(os.path.join(dirName, subdir), image_ext)
                return_images.extend(updated_files)

    return return_images


def rename_image(image_file, storage_directory='.', dryrun=False, verbose=False):
    """ Extracts the metadata for the given image and puts the file in a folder based on year-month.

    https://stackoverflow.com/questions/237079/how-do-i-get-file-creation-and-modification-date-times
    fname = pathlib.Path('test.py')
    ctime = datetime.datetime.fromtimestamp(fname.stat().st_ctime, tz=datetime.timezone.utc)
    mtime = datetime.datetime.fromtimestamp(fname.stat().st_mtime, tz=datetime.timezone.utc)

    Returns 1 if the file was copied successfully, 0 otherwise
    """
    # Store the file name
    file_name = os.path.basename(image_file)

    if verbose:
        print(f'Processing {file_name}.')
    # Read the image data using PIL
    try:
        oimage = Image.open(image_file)
    except OSError:
        print(f'Error: Could not open {image_file}.')
        return 0
    fname = pathlib.Path(image_file)
    ctime = datetime.datetime.fromtimestamp(fname.stat().st_ctime, tz=datetime.timezone.utc)
    mtime = datetime.datetime.fromtimestamp(fname.stat().st_mtime, tz=datetime.timezone.utc)
    earliest_date = min(ctime, mtime)
    # Extract exif data
    exifdata = oimage.getexif()
    if exifdata:
        for tag_id in exifdata:
            # Get the tag name
            tag = TAGS.get(tag_id, tag_id)
            if tag is not str:
                continue
            data = exifdata.get(tag_id)
            # Only use the datetime tag
            if tag.lower() == 'datetime':
                try:
                    parsed_date = datetime.datetime.strptime(data, '%Y:%m:%d %H:%M:%S')
                except ValueError:
                    parsed_date = datetime.datetime.today()
                parsed_date = datetime.datetime.combine(parsed_date, datetime.time.min, tzinfo=datetime.timezone.utc)
                earliest_date = min(earliest_date, parsed_date)
    month = earliest_date.strftime('%B')
    place_to_store = os.path.join(storage_directory, f'{earliest_date.year}', f'{month}', file_name)

    if verbose:
        print(f'Copying {image_file} to {place_to_store}')
    if dryrun:
        return 1
    os.makedirs(os.path.dirname(place_to_store), exist_ok=True)
    try:
        shutil.copy(image_file, place_to_store)
    except PermissionError as e:
        print(f'Could not move {image_file} to {place_to_store}: {e}')
        return 0
    return 1


if __name__ == "__main__":

    # Parse user supplied information
    parser = argparse.ArgumentParser(prog='Picture Organizer',
                                     description='Organizes images into separate directories.')
    parser.add_argument('starting_directory', help='Directory from which to start searching for images.',
                        type=pathlib.Path)
    parser.add_argument('storage_directory', help='Directory where images will be stored.',
                        type=pathlib.Path)
    parser.add_argument('-f', '--filetype',
                        help='Extension to search for. Default is jpg', type=str, default='jpg')
    parser.add_argument('-d', '--dryrun',
                        help='If true, only prints to screen what files would be moved to.', type=bool, default=False)
    parser.add_argument('-v', '--verbose',
                        help='If True, prints additional information to screen, such as file names.', type=bool,
                        default=False)

    args = parser.parse_args()

    found_images = find_images(args.starting_directory, args.filetype)

    print(f'Found {len(found_images)} images. Processing.')

    tot_moved = 0

    for image in found_images:
        num_moved = rename_image(image, args.storage_directory, dryrun=args.dryrun, verbose=args.verbose)
        tot_moved += num_moved

    msg = f'Copied {tot_moved} images to {args.storage_directory}'
    if tot_moved == len(found_images):
        msg += f'\n\tAll images were copied. Safe to delete {args.starting_directory}.'

    print(msg)
