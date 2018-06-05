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

	def hash_object(self, data, obj_type, write=True):
		"""Compute hash of object data of given type and write to object store
    	if "write" is True. Return SHA-1 object hash as hex string.
    	"""
		header = '{},{}'.format(obj_type, len(data)).encode()
		full_data = header + b'\x00' + data
		sha1 = hashlib.sha1(full_data).hexdigest()
		if write:
			path = os.path.join('.git', 'objects', sha1[:2], sha1[2:])
			if not os.path.exists(path):
				os.makedirs(os.path.dirname(path), exist_ok = True)
				self.write_file(path, zlib.compress(full_data))

		return sha1

	def read_index(self):
		"""Read git index file and return list of IndexEntry objects."""

		try:
			data = self.read_file(os.path.join('.git', 'index'))
		except FileNotFoundError:
			return []

		digest = hashlib.sha1(data[:-20]).digest()
		assert digest == data[-20:], 'invalid index checksum'
		signature, version, num_entries = struct.unpack('!4sLL', data[:12])
		assert signature == b'DIRC', \
			'invalid index signature {}'.format(signature)
		assert version == 2, 'unknown index version {}'.format(version)
		entry_data = data[12:-20]
		entries = []
		i = 0
		while i + 62 < len(entry_data):
			fields_end = i + 62
			fields = struct.unpack('!LLLLLLLLLL20sH', entry_data[i:fields_end])
			path_end = entry_data.index(b'\x00', fields_end)
			path = entry_data[fields_end:path_end]
			entry = IndexEntry(*(fields + (path.decode(),)))
			entries.append(entry)
			entry_len = ((62 + len(path) + 8) // 8) * 8
			i += entry_len
		
		assert len(entries) == num_entries
		return entries


		













