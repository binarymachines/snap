#!/usr/bin/env python

import os
import sh
from sh import git

VERSION_NUM = '1.0.6'
VERSION_MODULE_TEMPLATE = '''#!/usr/bin/env python
VERSION_STRING = "{version_string}"

def show():
    return VERSION_STRING

def main():
    print(VERSION_STRING)

if __name__ == '__main__':
    main()
'''

def main():        
    git_hash = git.describe('--always').lstrip().rstrip()
    version = '%s [%s]' % (VERSION_NUM, git_hash)
    print(VERSION_MODULE_TEMPLATE.format(version_string=version))

if __name__ == '__main__':
    main()

