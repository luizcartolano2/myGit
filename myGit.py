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

	def write_tree(self):
		"""Write a tree object from the current index entries."""
		tree_entries = []
		for entry in self.read_index():
			assert '/' not in entry.path, \
			    'currently only supports a single, top-level directory'
			mode_path = '{:o} {}'.format(entry.mode, entry.path).encode()
			tree_entry = mode_path + b'\x00' + entry.sha1
			tree_entries.append(tree_entry)
		return self.hash_object(b''.join(tree_entries), 'tree')

	def commit(self, message, author):
		"""Commit the current state of the index to master with given message.
		Return hash of commit object.
		"""
		tree = self.write_tree()
		parent = self.get_local_master_hash()
		timestamp = int(time.mktime(time.localtime()))
		utc_offset = -time.timezone
		author_time = '{} {}{:02}{:02}'.format(
			timestamp,
			'+' if utc_offset > 0 else '-',
			abs(utc_offset) // 3600,
			(abs(utc_offset) // 60) % 60)
		lines = ['tree ' + tree]
		if parent:
			lines.append('parent ' + parent)
		lines.append('author {} {}'.format(author, author_time))
		lines.append('committer {} {}'.format(author, author_time))
		lines.append('')
		lines.append(message)
		lines.append('')
		data = '\n'.join(lines).encode()
		sha1 = self.hash_object(data, 'commit')
		master_path = os.path.join('.git', 'refs', 'heads', 'master')
		self.write_file(master_path, (sha1 + '\n').encode())
		print('committed to master: {:7}'.format(sha1))
		return sha1
		

	def extract_lines(self, data):
	    """Extract list of lines from given server data."""
	    lines = []
	    i = 0
	    for _ in range(1000):
	        line_length = int(data[i:i + 4], 16)
	        line = data[i + 4:i + line_length]
	        lines.append(line)
	        if line_length == 0:
	            i += 4
	        else:
	            i += line_length
	        if i >= len(data):
	            break
	    return lines

	def build_lines_data(self, lines):
	    """Build byte string from given lines to send to server."""
	    result = []
	    for line in lines:
	        result.append('{:04x}'.format(len(line) + 5).encode())
	        result.append(line)
	        result.append(b'\n')
	    result.append(b'0000')
	    return b''.join(result)

	def http_request(self, url, username, password):
	    response = requests.get(url, auth=(username, password))
	    response.raise_for_status()
	    return response.content	 

	def get_remote_master_hash(self, git_url, username, password):
	    """Get commit hash of remote master branch, return SHA-1 hex string or
	    None if no remote commits.
	    """
	    url = git_url + '/info/refs?service=git-receive-pack'
	    response = self.http_request(url, username, password)
	    lines = extract_lines(response)
	    assert lines[0] == b'# service=git-receive-pack\n'
	    assert lines[1] == b''
	    if lines[2][:40] == b'0' * 40:
	        return None
	    master_sha1, master_ref = lines[2].split(b'\x00')[0].split()
	    assert master_ref == b'refs/heads/master'
	    assert len(master_sha1) == 40
	    return master_sha1.decode()

	def find_tree_objects(self, tree_sha1):
	    """Return set of SHA-1 hashes of all objects in this tree
	    (recursively), including the hash of the tree itself.
	    """
	    objects = {tree_sha1}
	    for mode, path, sha1 in self.read_tree(sha1=tree_sha1):
	        if stat.S_ISDIR(mode):
	            objects.update(self.find_tree_objects(sha1))
	        else:
	            objects.add(sha1)
	    return objects

	def find_commit_objects(self, commit_sha1):
	    """Return set of SHA-1 hashes of all objects in this commit
	    (recursively), its tree, its parents, and the hash of the commit
	    itself.
	    """
	    objects = {commit_sha1}
	    obj_type, commit = self.read_object(commit_sha1)
	    assert obj_type == 'commit'
	    lines = commit.decode().splitlines()
	    tree = next(l[5:45] for l in lines if l.startswith('tree '))
	    objects.update(self.find_tree_objects(tree))
	    parents = (l[7:47] for l in lines if l.startswith('parent '))
	    for parent in parents:
	        objects.update(self.find_commit_objects(parent))
	    return objects

	def find_missing_objects(self, local_sha1, remote_sha1):
	    """Return set of SHA-1 hashes of objects in local commit that are
	    missing at the remote (based on the given remote commit hash).
	    """
	    local_objects = self.find_commit_objects(local_sha1)
	    if remote_sha1 is None:
	        return local_objects
	    remote_objects = self.find_commit_objects(remote_sha1)
	    return local_objects - remote_objects

	def encode_pack_object(self, obj):
	    """Encode a single object for a pack file and return bytes
	    (variable-length header followed by compressed data bytes).
	    """
	    obj_type, data = self.read_object(obj)
	    type_num = ObjectType[obj_type].value
	    size = len(data)
	    byte = (type_num << 4) | (size & 0x0f)
	    size >>= 4
	    header = []
	    while size:
	        header.append(byte | 0x80)
	        byte = size & 0x7f
	        size >>= 7
	    header.append(byte)
	    return bytes(header) + zlib.compress(data)

	def create_pack(self, objects):
	    """Create pack file containing all objects in given given set of
	    SHA-1 hashes, return data bytes of full pack file.
	    """
	    header = struct.pack('!4sLL', b'PACK', 2, len(objects))
	    body = b''.join(self.encode_pack_object(o) for o in sorted(objects))
	    contents = header + body
	    sha1 = hashlib.sha1(contents).digest()
	    data = contents + sha1
	    return data

	def push(self, git_url, username, password):
	    """Push master branch to given git repo URL."""
	    remote_sha1 = self.get_remote_master_hash(git_url, username, password)
	    local_sha1 = self.get_local_master_hash()
	    missing = self.find_missing_objects(local_sha1, remote_sha1)
	    lines = ['{} {} refs/heads/master\x00 report-status'.format(
	            remote_sha1 or ('0' * 40), local_sha1).encode()]
	    data = self.build_lines_data(lines) + self.create_pack(missing)
	    url = git_url + '/git-receive-pack'
	    response = self.http_request(url, username, password, data=data)
	    lines = self.extract_lines(response)
	    assert lines[0] == b'unpack ok\n', \
	        "expected line 1 b'unpack ok', got: {}".format(lines[0])
