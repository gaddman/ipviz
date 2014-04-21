#! /usr/bin/env python2

# Given a list of subnets, produce a visualisation of them.
# IPv4 only
# Christopher Gadd
# 10/04/2014

from __future__ import print_function	# because screw Nathan and python2
import argparse
import ipaddress # python3 has as standard, for python2 use backport py2-ipaddress
# for the image creation:
from random import random
from PIL import Image, ImageDraw
from colorsys import hsv_to_rgb

grc = 0.618033988749895 # golden ratio conjugate
rh = 10					# row height

parser = argparse.ArgumentParser()
parser.add_argument ("inputFile", help="a file list of IP ranges")
parser.add_argument ("-s", "--subnetSize", help="smallest size of subnet to print", default=24, type=int)
parser.add_argument ("-S", "--supernetSize", help="subnet size at which to wrap to next line", type=int)
parser.add_argument ("-b", "--blobSize", help="size of blob representing the smallest subnet", default=4, type=int)
parser.add_argument ("-t", "--text", help="output as text", dest="textOut", action='store_true', default=True)
parser.add_argument ("--notext", help="don't output as text", dest="textOut", action='store_false')
parser.add_argument ("-i", "--image", help="output as image", dest="imageOut", action='store_true', default=True)
parser.add_argument ("--noimage", help="don't output as image", dest="imageOut", action='store_false')
parser.add_argument ("-o", "--outputFile", help="filename for output image", default="ipviz.png", type=str)
args = parser.parse_args()
globals().update(vars(args))

ipranges = [line.split() for line in open(inputFile)]

# set default label where missing and create colour dictionary
labels={}
for thisRange in ipranges:
	try:
		thisRange[1] = thisRange[1]
	except IndexError:
		thisRange.append("O")
	if thisRange[1] not in labels:
		hue = random() # use random start value
		hue = (hue+grc) % 1 # based on http://martin.ankerl.com/2009/12/09/how-to-create-random-colors-programmatically/
		labels[thisRange[1]] = hue

#print (ipranges)
#print (labels)

# convert string to IPv4Network
networks = [[ipaddress.ip_network(thisRange[0]),thisRange[1]] for thisRange in ipranges]
networks.sort()
#print (networks)
# set supernetSize to match smallest prefix
if (not supernetSize):
	supernetSize = min([thisNet[0].prefixlen for thisNet in networks])

# find supernet for each network
superNets = []
for thisNet in networks:
	if thisNet[0].prefixlen<supernetSize:
		# our network of interest is larger than the supernet we want to display, so split into subnets
		superNets.extend(thisNet[0].subnets(new_prefix=supernetSize))
	else:
		# our network of interest is smaller or equal to the supernet we want to display, drop it straight in
		superNets.append(thisNet[0].supernet(new_prefix=supernetSize))
# now remove dupes and sort
superNets = sorted(list(set(superNets)))
#print ([thisNet[0].exploded for thisNet in superNets])

# now we know how wide and tall the image will be
bt = (0,-rh)					# top left of blob
bb = (bt[0]+blobSize,bt[1]+rh)	# bottom right of blob
lineCol = "#C0C0C0"		# colour of dividing line
size = (blobSize*len(list(superNets[0].subnets(new_prefix = subnetSize))), rh*len(list(superNets))+rh*len(labels))
img = Image.new('RGB',size)
draw = ImageDraw.Draw(img)

# print legend
if (textOut):
	print ("These are all the networks to visualise:")
	print ([thisNet[0].exploded for thisNet in networks])
	print ()
	print ("Each row is a /{} and each point represents a /{} subnet".format(supernetSize,subnetSize))
	print (". = no network, lowercase = partially covered, uppercase = completely covered\n")
for thisLabel in labels:
	# full subnet
	bt=(0,bt[1]+rh)
	bb=(img.size[0]/2,bt[1]+rh)
	netFill = tuple(int(x*256) for x in hsv_to_rgb(labels[thisLabel], 0.99, 0.99))
	draw.rectangle([bt,bb], fill=netFill)
	draw.text(bt,text=thisLabel+" full subnet",fill="#000000")
	# partial subnet
	bt=(img.size[0]/2,bt[1])
	bb=(img.size[0],bb[1])
	netFill = tuple(int(x*256) for x in hsv_to_rgb(labels[thisLabel], 0.3, 0.99))
	draw.rectangle([bt,bb], fill=netFill)
	draw.text(bt,text=thisLabel+" partial subnet",fill="#000000")
bt=(0,bt[1]+rh)
bb=(blobSize,bt[1]+rh)

# loop through each superNet and print subNets
for thisSuper in superNets:
	if (textOut):
		print (thisSuper)

	# find matching networks of interest
	inclNets = [thisNet for thisNet in networks if thisSuper.overlaps(thisNet[0])]
#	print (inclNets)

	# determine all the subnets in this supernet
	subNets = thisSuper.subnets(new_prefix = subnetSize)
	for thisSub in subNets:
		# now see if this subnet is covered in our matching network list
		netChar = "."
		netFill = (0,0,0)	# R,G,B
		for thisNet in inclNets:
			if (thisSub.overlaps(thisNet[0])):
				# got a matching network. Need to look again at this, it will match on a network too small (is that ok?)
				if (thisNet[0].prefixlen <= thisSub.prefixlen):
					# subnet totally covered - uppercase and darker
					netChar = thisNet[1][:1].upper()
					netFill = tuple(int(x*256) for x in hsv_to_rgb(labels[thisNet[1]], 0.99, 0.99))
					break
				else:
					# subnet partially covered - lowercase or lighter
					netChar = thisNet[1][:1].lower()
					netFill = tuple(int(x*256) for x in hsv_to_rgb(labels[thisNet[1]], 0.3, 0.99))
			elif (thisNet[0].network_address>thisSub.broadcast_address):
				# step out of for loop once we've gone past the subnet under test
				break
			# no matching network
		# print (text) or draw (image) this subnet
		if (textOut):
			print (netChar,end="") # python3
		#print (bt,netFill)
		draw.rectangle([bt,bb], fill=netFill)
		draw.line([bt,(bt[0],bt[1]+rh)],fill=lineCol,width=1)
		bt=(bt[0]+blobSize,bt[1])
		bb=(bt[0]+blobSize,bt[1]+rh)
	# end of supernet, print EOL (text) or print network (image)
	if (textOut):
		print()	# python3
	draw.text((0,bt[1]),text=thisSuper.exploded,fill=lineCol)
	bt=(0,bt[1]+rh)
	bb=(blobSize,bt[1]+rh)

# finally save completed image
if (imageOut):
	img.save(outputFile)