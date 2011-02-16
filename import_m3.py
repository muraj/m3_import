#!BPY

"""
Name: 'm3 file (.m3)...'
Blender: 249
Group: 'Import'
Tooltip: 'Import m3 File Format (.m3)'
"""

__author__ = "Cory Perry (muraj)"
__url__ = ("blender", "blenderartists.org",
"Author's homepage, http://zijin.ath.cx/")
__version__ = ""

__bpydoc__ = """\
This script imports m3 format files to Blender.

The m3 file format, used by Blizzard in several games, is based around the
mdx and m2 file format.  Thanks to the efforts of Volcore, madyavic and the
people working on libm3, the file format has been reversed engineered
enough to make this script possible (Thanks guys!).

This script currently imports the following:<br>
 - Geometry data (vertices, faces, submeshes [in vertex groups])
 - Model Textures (currently only the first material is supported)
 
   Blender supports the DDS file format and needs the image in the same
   directory.  This script will notify you of any missing textures.

 - Bone Data (no animations yet)

TODO:<br>
 - Documentation & clean up
 - Adjust vertices to bind pose (import IREF matrices)
 - Import Animation data

Usage:<br>
	Execute this script from the "File->Import" menu and choose a m3 file to
open.

Notes:<br>
	Generates the standard verts and faces lists.
"""
import Blender
from Blender.Mathutils import *
import struct
##################
## Struct setup ##
##################
class ref:
	fmt = 'LL'
	def __init__(self, file):
		_s=file.read(struct.calcsize(self.fmt))
		self.entries, self.refid = struct.unpack(self.fmt, _s)
class animref:
	fmt = 'HHL'
	def __init__(self, file):
		_s=file.read(struct.calcsize(self.fmt))
		self.flags, self.animflags, self.animid = struct.unpack(self.fmt, _s)
class Tag:
	fmt = '4sLLL'
	def __init__(self, file):
		_s=file.read(struct.calcsize(self.fmt))
		self.name, self.ofs, self.nTag, self.version = struct.unpack(self.fmt, _s)
class matrix:
	fmt='f'*16
	def __init__(self, file):
		_s=file.read(struct.calcsize(self.fmt))
		self.mat = struct.unpack(self.fmt, _s)
class vect:
	fmt='fff'
	def __init__(self, file):
		_s=file.read(struct.calcsize(self.fmt))
		self.v = struct.unpack(self.fmt, _s)
class vert:
	fmt="4B4b4B%dH4B"
	ver = { 0x020000: 2, 0x060000: 4, 0x0A0000: 6, 0x120000: 8 }
	def __init__(self, file, flag):
		self.pos = vect(file)
		fmt = self.fmt % (self.ver[flag])
		_s=file.read(struct.calcsize(fmt))
		_s = struct.unpack(fmt, _s)
		self.boneWeight = _s[0:4]
		self.boneIndex = _s[4:8]
		self.normal = _s[8:12]
		self.uv = _s[12:14]
		self.tan = _s[-4:]	#Skipping the middle ukn value if needed
		self.boneWeight = [b/255.0 for b in self.boneWeight]
		self.normal = [x*2.0/255.0-1.0 for x in self.normal]
		self.tan = [x*2.0/255.0-1.0 for x in self.tan]
		self.uv = [x/2046.0 for x in self.uv]
		self.uv[1] = 1.0 - self.uv[1]
	@classmethod
	def size(cls, flag):
		return struct.calcsize(cls.fmt % (cls.ver[flag]))
class quat:
	fmt='ffff'
	def __init__(self, file):
		_s=file.read(struct.calcsize(self.fmt))
		self.v = struct.unpack(self.fmt, _s)
		self.v = [self.v[-1], self.v[0], self.v[1], self.v[2]]	#Quats are stored x,y,z,w - this fixes it
class bone:
	def __init__(self, file):
		file.read(4)	#ukn1
		self.name = ref(file)
		self.flag, self.parent, _ = struct.unpack('LhH',file.read(8))
		self.posid = animref(file)
		self.pos = vect(file)
		file.read(4*4)	#ukn
		self.rotid = animref(file)
		self.rot = quat(file)
		file.read(4*5)	#ukn
		self.scaleid = animref(file)
		self.scale = vect(file)
		vect(file)		#ukn
		file.read(4*6)	#ukn
class div:
	def __init__(self, file):
		self.faces = ref(file)
		self.regn = ref(file)
		self.bat = ref(file)
		self.msec = ref(file)
		file.read(4)	#ukn
class regn:
	fmt = 'LHHLL6H'
	def __init__(self, file):
		_s=file.read(struct.calcsize(self.fmt))
		_ukn1, self.ofsVert, self.nVerts, self.ofsIndex, self.nIndex, \
			self.boneCount, self.indBone, self.nBone = struct.unpack(self.fmt, _s)[:8]
class mat:
	def __init__(self, file):
		self.name = ref(file)
		file.read(4*10)	#ukn
		self.layers = [ref(file) for _ in range(13)]
		file.read(4*15)	#ukn
class layr:
	def __init__(self, file):
		file.read(4)
		self.name = ref(file)
		#Rest not implemented.
class hdr:
	fmt = '4sLL'
	def __init__(self, file):
		_s = file.read(struct.calcsize(self.fmt))
		self.magic, self.ofsTag, self.nTag = struct.unpack(self.fmt, _s)
		self.MODLref = ref(file)
class MODL:
	def __init__(self, file, flag=20):
		self.name = ref(file)
		self.ver = struct.unpack('L',file.read(4))[0]
		self.seqHdr = ref(file)
		self.seqData = ref(file)
		self.seqLookup = ref(file)
		file.read(4*3)			#ukn1
		self.STS = ref(file)
		self.bones = ref(file)
		file.read(4)			#ukn2
		self.flags = struct.unpack('L',file.read(4))[0]
		self.vert = ref(file)
		self.views = ref(file)
		self.boneLookup = ref(file)
		self.extents = [vect(file), vect(file)]
		self.radius = struct.unpack('f',file.read(4))[0]
		file.read(4*13)			#ukn4
		self.attach = ref(file)
		self.attachLookup = ref(file)
		self.lights = ref(file)
		if flag == 23: ref(file)	#SHBX?	Only in MODL23
		self.cameras = ref(file)
		ref(file)	#D?
		self.materialsLookup = ref(file)
		self.materials = ref(file)
		#rest unknown/varies with version/unneeded
###################
## Read file format
###################
def read(filename):
	"""Opens the file "filename" and imports as an m3 file"""
	t = Blender.sys.time()
	editmode = Blender.Window.EditMode()
	if editmode: Blender.Window.EditMode(0)
	Blender.Window.WaitCursor(1)
	Blender.Window.DrawProgressBar(0.0, 'Opening File')
	dir = Blender.sys.dirname(filename)
	with open(filename, 'rb') as file:
		h=hdr(file)
		if not h.magic == '33DM':
			raise Exception('m3_import: !ERROR! Not a valid or supported m3 file')
		file.seek(h.ofsTag)	#Jump to the Tag table
		Blender.Window.DrawProgressBar(0.05, 'Reading TagTable')
		tagTable = [Tag(file) for _ in range(h.nTag)]
		file.seek(tagTable[h.MODLref.refid].ofs)
		m = MODL(file, tagTable[h.MODLref.refid].version)
		if not m.flags & 0x20000: raise Exception('m3_import: !ERROR! Model doesn\'t contain any vertices')
		vert_flags = m.flags & 0x1E0000		#Mask out the vertex version
		file.seek(tagTable[m.vert.refid].ofs)
		Blender.Window.DrawProgressBar(0.05, 'Reading Vertices')
		verts = [ vert(file, vert_flags) for _ in range(tagTable[m.vert.refid].nTag / vert.size(vert_flags)) ]
		file.seek(tagTable[m.views.refid].ofs)
		d = div(file)
		file.seek(tagTable[d.regn.refid].ofs)
		regnTable = [regn(file) for _ in range(tagTable[d.regn.refid].nTag)]
		file.seek(tagTable[d.faces.refid].ofs)
		Blender.Window.DrawProgressBar(0.10, 'Reading Faces')
		faceTable = struct.unpack('H'*(tagTable[d.faces.refid].nTag), file.read(tagTable[d.faces.refid].nTag*2))
		mesh = Blender.Mesh.New()
		mesh.name = Blender.sys.splitext(Blender.sys.basename(filename))[0]
		scn = Blender.Scene.GetCurrent()
		for o in scn.objects: o.sel = 0
		Blender.Window.DrawProgressBar(0.25, 'Allocating Blender Objects')
		for i in range(tagTable[d.regn.refid].nTag):
			##Face indices are stored per submesh - could be done better, but meh
			v = verts[regnTable[i].ofsVert : regnTable[i].ofsVert+regnTable[i].nVerts]
			mesh.verts.extend([vv.pos.v for vv in v])
			f = faceTable[regnTable[i].ofsIndex : regnTable[i].ofsIndex+regnTable[i].nIndex]
			f = [[f[j*3], f[j*3+1], f[j*3+2]] for j in range(len(f)/3)]
			mesh.faces.extend(f)
			print len(f), len(mesh.faces), len(v)
			for j in range(-1,-len(f),-1):
				##Set the uv coordinates (stored in the file's vert struct) to each newly added face (iterating backwards for less complexity)
				mesh.faces[j].uv = [Vector(verts[f[j][0]].uv), Vector(verts[f[j][1]].uv), Vector(verts[f[j][2]].uv)]
				mesh.faces[j].mat = 0				#TODO: get the real index
				mesh.faces[j].smooth = 1
		mesh.faceUV = True
		Blender.Window.DrawProgressBar(0.35, 'Calculating Normals')
		mesh.calcNormals()
		meshobj = scn.objects.new(mesh)
		for i in range(tagTable[d.regn.refid].nTag):
			##Setup the vertex groups for each submesh - right way to do this?
			grpname = "Group%02d" % (i)
			mesh.addVertGroup(grpname)
			mesh.assignVertsToGroup(grpname, [j+regnTable[i].ofsVert for j in range(regnTable[i].nVerts)], 1.0, Blender.Mesh.AssignModes.REPLACE)
		Blender.Window.DrawProgressBar(0.40, 'Loading Materials')
		matl = Blender.Material.New('Mat01')		#TODO: Import all the materials.
		mesh.materials = [matl]
		matl.mode |= Blender.Material.Modes.ZTRANSP	#Allow for transparency - doesn't seem to work...
		file.seek(tagTable[m.materials.refid].ofs)
		mm = mat(file)
		for map,i in [(Blender.Texture.MapTo.COL,0), (Blender.Texture.MapTo.SPEC,2), (Blender.Texture.MapTo.NOR,9)]:	#TODO: Add emissive too (doesn't seem to work)
			##Run through the known layers in a material (layer 0 is diffuse, layer 2 is Specular, layer 3 is emissive, layer 9 is normal map)
			##and load up the required images
			file.seek(tagTable[mm.layers[i].refid].ofs)
			nref = layr(file).name
			file.seek(tagTable[nref.refid].ofs)
			path = Blender.sys.join(dir, Blender.sys.basename(file.read(nref.entries)))
			tex = Blender.Texture.New(Blender.sys.basename(path))
			tex.setType('Image')
			if map == Blender.Texture.MapTo.NOR:
				tex.setImageFlags('NormalMap')
			try:
				tex.setImage(Blender.Image.Load(path))
			except Exception as e:
				print "m3_import: !Warning! File '%s' not available\n\n%s" % (tex.name, e)
			matl.setTexture(i, tex, Blender.Texture.TexCo.UV, map)
		meshobj.setMaterials([matl])
		Blender.Redraw()
		Blender.Window.DrawProgressBar(0.60, 'Reading Bones')
		if tagTable[m.bones.refid].nTag > 0:
			##Read the bone structures and create the armature.
			##Much of this code was referenced from the ms3d importer
			obj = Blender.Object.New('Armature', 'm3 Skeleton')
			armature = Blender.Armature.New('m3 Skeleton')
			armature.drawType = Blender.Armature.STICK
			obj.link(armature)
			scn.objects.link(obj)
			#obj.makeParentDeform([mesh])	#TODO: Needs mesh in bind pose
			armature.makeEditable()
			file.seek(tagTable[m.bones.refid].ofs)
			bones = [ bone(file) for _ in range(tagTable[m.bones.refid].nTag)]
			boneNames = []
			for b in bones:
				file.seek(tagTable[b.name.refid].ofs)
				boneNames.append(file.read(b.name.entries-1))	#Skipping the \0
			for i,b in enumerate(bones):
				bb = Blender.Armature.Editbone()
				armature.bones[boneNames[i]] = bb
				if b.parent > -1:
					bb.parent = armature.bones[boneNames[b.parent]]
					bb.head = Vector(b.pos.v) * bb.parent.matrix + bb.parent.head
					bb.matrix = Quaternion(b.rot.v).toMatrix() * bb.parent.matrix
				else:
					bb.head = Vector(b.pos.v)
					bb.matrix = Quaternion(b.rot.v).toMatrix()
				_vec = bb.tail - bb.head
				_vec.normalize()
				bb.tail = bb.head + 0.001 * _vec
			armature.update()
		#TODO: Transform mesh to bind pose, read animations, etc
	Blender.Window.WaitCursor(0)
	Blender.Window.DrawProgressBar(1.0, 'Finished')
	if editmode: Blender.Window.EditMode(1)	#Just being nice
	print "Imported \"%s\" in %.4f seconds" % (Blender.sys.basename(filename), Blender.sys.time() - t)
def main():
	Blender.Window.FileSelector(read, 'm3 Import', Blender.sys.makename(ext='.m3'))
if __name__ == '__main__':
	main()