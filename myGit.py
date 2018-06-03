"""
	Implement just enough git to commit and push to GitHub.
	Read the story here: http://benhoyt.com/writings/pygit/
	Released under a permissive MIT license (see LICENSE.txt).
"""

import argparse, collections, difflib, enum, hashlib, operator, os, stat
import struct, sys, time, urllib, zlib
import requests

# Data for one entry in the git index (.git/index)
IndexEntry = collections.namedtuple('IndexEntry', [
    'ctime_s', 'ctime_n', 'mtime_s', 'mtime_n', 'dev', 'ino', 'mode', 'uid',
    'gid', 'size', 'sha1', 'flags', 'path',
])

class ObjectType(enum.Enum):
    """Object type enum. There are other types too, but we don't need them.
    See "enum object_type" in git's source (git/cache.h).
    """
    commit = 1
    tree = 2
    blob = 3

class MyGit(object):
	"""docstring for MyGit"""
	def __init__(self):
		return
		

	def read_file(self,path):
		"""Read contents of file at given path as bytes."""
		with open(path, 'rb') as f:
			return f.read()

	def write_file(self, path, data):
		"""Write data bytes to file at given path."""
		with open(path, 'wb') as f:
			f.write(data)

	def init(self, repo):
		"""Create directory for repo and initialize .git directory."""
		os.mkdir(repo)
		os.mkdir(os.path.join(repo, '.git'))
		for name in ['objects', 'refs', 'refs/heads']:
			os.mkdir(os.path.join(repo, '.git', name))
		self.write_file(path=os.path.join(repo, '.git', 'HEAD'),data=b'ref: refs/heads/master')
		print('initialized empty repository: {}'.format(repo))