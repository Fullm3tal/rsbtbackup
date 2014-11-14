#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Rsyncbtrfs [version 1.0.1]
#
# Rsyncbtrfs is a simple incremental backup tool which uses the 
# incremental snapshot capability of a Btrfs subvolume.
#
# Copyright 2014 Adrien Ferrand <ferrand.ad@gmail.com>
#
# This program is free software: you can redistribute it and/or modify it 
# under the terms of the GNU General Public License as published by the 
# Free Software Foundation, either version 3 of the License, or (at your 
# option) any later version.
#
# This program is distributed in the hope that it will be useful, but 
# WITHOUT ANY WARRANTY; without even the implied warranty of 
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU 
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License along 
# with this program. If not, see <http://www.gnu.org/licenses/>.

# Rsyncbtrfs class definition
class RsyncBtrfs:
    # This function initiates a backup directory args.DESTPATH
    def init(self,args):
        print "Initialization of backup directory '%s'" % (args.DESTPATH)
        if not os.path.isfile(args.DESTPATH+"/.log/rsyncbtrfs"):
            if not os.path.isdir(args.DESTPATH+"/.log"):
                os.mkdir(args.DESTPATH+"/.log")
            try:
                open(args.DESTPATH+"/.log/rsyncbtrfs","a").close()
            except:
                print "Error : invalid backup directory"

    # This function executes a backup of args.SRCPATH on args.DESTPATH
    def backup(self,args):
        date_now_str = datetime.datetime.today().strftime('%Y-%m-%d-%H:%M:%S')
        if not os.path.isdir(args.DESTPATH):
            print "Error : invalid backup directory"
            exit()
        if not os.path.isfile(args.DESTPATH+"/.log/rsyncbtrfs"):
            print "The given backup directory is not initiated. The following command must be executed before any backup : 'rsyncbtrfs init %s'" % (args.DESTPATH)
            exit()
        logger = self.start_logging(args.DESTPATH+"/.log")
        logger.info("The backup of '%s' on '%s' has started" % (args.SRCPATH,args.DESTPATH)) 
        # Creation of a Btrfs subvolume and start of the backup
        #fnull = open(os.devnull,'w')
        if os.path.isdir(args.DESTPATH+"/cur"):
        # No backup has been done yet : full backup
            if not os.path.isdir(args.DESTPATH+"/pending"):
                self.subprocess_logged(["/sbin/btrfs","subvolume","snapshot",args.DESTPATH+"/"+os.readlink(args.DESTPATH+"/cur"),args.DESTPATH+"/pending"],logger)
            retcode = self.subprocess_logged(["/usr/bin/rsync","--delete","--delete-before","--delete-excluded","--inplace","--no-whole-file","-a",args.SRCPATH+"/",args.DESTPATH+"/pending"],logger)
        else:
        # At least one backup has already been done : incremental backup
            if not os.path.isdir(args.DESTPATH+"/pending"):
                self.subprocess_logged(["/sbin/btrfs","subvolume","create",args.DESTPATH+"/pending"],logger)
            retcode = self.subprocess_logged(["/usr/bin/rsync","-a",args.SRCPATH+"/",args.DESTPATH+"/pending"],logger)
        # We check if everything went well
        if retcode :
            logger.error("An error occured during rsync execution. A pending backup lies in '%s'" % (args.DESTPATH+"/pending"))
            raise OSError()
            exit()
        # The backup has been done without issue. The subvolume takes its final name. The symlink cur points on the latter.
        self.subprocess_logged(["/bin/rm","-f",args.DESTPATH+"/cur"],logger)
        self.subprocess_logged(["/bin/ln","-s",date_now_str,args.DESTPATH+"/cur"],logger)
        os.rename(args.DESTPATH+"/pending",args.DESTPATH+"/"+date_now_str)
        logger.info("The backup of '%s' on '%s' has ended without error" % (args.SRCPATH,args.DESTPATH))

    # This function activates the logging process of rsyncbtrfs
    def start_logging(self,path):
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s :: %(levelname)s :: %(message)s')
        file_handler = logging.handlers.RotatingFileHandler('%s/activity.log' % path, 'a', 1000000, 1)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        return logger

    # This function calls an os command with logging
    def subprocess_logged(self,execution_string,logger):
        process = subprocess.Popen(execution_string,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        stdout,stderr = process.communicate()
        if stdout:
            logger.info(stdout)
        if stderr:
            logger.error("An error occured during the execution of : %s" % execution_string)
            logger.error(stderr)
            # The function returns True in order to raise the exception
            return True
        # Everything went well, the function returns False
        return False

# Rsyncbtrfs execution by a shell
if __name__ == "__main__":
    # Initiate
    rsyncbtrfs = RsyncBtrfs()

    # Rsyncbtrfs entry parameters handler
    parser = argparse.ArgumentParser(description='Incremental backup over Btrfs subvolumes tool')
    subparsers = parser.add_subparsers(help='Available commands')

    # Init parser options
    init_parser = subparsers.add_parser('init',description='Initiate a backup directory')
    init_parser.add_argument('DESTPATH',action='store',help='Backup directory path')
    init_parser.set_defaults(func=rsyncbtrfs.init)

    # Backup parser options
    backup_parser = subparsers.add_parser('backup',description='Do an incremental backup')
    backup_parser.add_argument('SRCPATH',action='store',help='Source directory path (local or remote)')
    backup_parser.add_argument('DESTPATH',action='store',help='Backup directory path')
    backup_parser.set_defaults(func=rsyncbtrfs.backup)

    # Handling entry parameters and ad-hoc function execution if needed
    args = parser.parse_args()
    args.func(args)