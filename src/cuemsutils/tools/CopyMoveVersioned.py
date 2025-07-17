import os
import shutil
from .log import Logger

class CopyMoveVersioned():

    @staticmethod
    def move(orig_path, dest_path, dest_filename=None):
        i = 0
        if dest_filename is None:
            dest_filename = os.path.basename(orig_path)
            
        (base, ext) = os.path.splitext(dest_filename)
        
        while True:     
            if not os.path.exists(os.path.join(dest_path, dest_filename)):
                Logger.debug('moving file to: {}'.format(os.path.join(dest_path, dest_filename)))
                shutil.move( orig_path, os.path.join(dest_path, dest_filename))
                break
            else:
                i += 1
                dest_filename = base + "-{:03d}".format(i) + ext
                continue    
        return dest_filename

    @staticmethod
    def copy_dir(orig_path, dest_path, dest_dirname):
        i = 0
        orig_name = dest_dirname
        while True:     
            if not os.path.exists(os.path.join(dest_path, dest_dirname)):
                Logger.debug('copyin dir to: {}'.format(os.path.join(dest_path, dest_dirname)))
                shutil.copytree( orig_path, os.path.join(dest_path, dest_dirname))
                break
            else:
                i += 1
                dest_dirname = orig_name + "-{:03d}".format(i)
                continue    
        return dest_dirname
