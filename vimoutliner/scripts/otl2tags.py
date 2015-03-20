#!/usr/bin/env python
# otl2tags.py
# Convert an OTL file to any tags-based file using config user-
# definable configuration files. HTML, OPML, XML, LATEX and
# many, many others should be easily supportables.
#
# Copyright (c) 2005-2010 Noel Henson All rights reserved

###########################################################################
# Basic function
#
#    This program accepts text outline files in Vim Outliners .otl format
#    and converts them to a tags-based equivalent

###########################################################################
# include whatever mdules we need

import sys
from ConfigParser import ConfigParser
import re

###########################################################################
# global variables

config = ConfigParser()     # configuration
linecount = 0        # outline size in lines
parents = []        # parent stack, (linenum, enum) enum is an order numer
v = {}            # variable dictionary for substitution
outline = []        # line tuples (value, indent)
output = []        # output outline
escapeDict = {}        # dictionary of character escape codes
debug = 0
inputfile = ""

###########################################################################
# arugment, help and debug functions


# usage
# print debug statements
# input: string
# output: string printed to standard out
def dprint(*vals):
    global debug
    if debug != 0:
        print >> sys.stderr, vals


# usage
# print the simplest form of help
# input: none
# output: simple command usage is printed on the console
def showUsage():
    print """
        Usage:
        otl2table.py [options] inputfile
        Options
            -c             config-file
            -d             debug
            --help         show help
        output filenames are based on the input file name and the config file
        """


# getArgs
# Check for input arguments and set the necessary switches
# input: none
# output: possible console output for help, switch variables may be set
def getArgs():
    global inputfile, debug, noTrailing, formatMode, config
    if (len(sys.argv) == 1):
        showUsage()
        sys.exit()()
    else:
        for i in range(len(sys.argv)):
            if (i != 0):
                if (sys.argv[i] == "-c"):         # test for the type flag
                    config.read(sys.argv[i + 1])  # read the config
                    i = i + 1                     # increment the pointer
                elif (sys.argv[i] == "-d"):
                    debug = 1
                elif (sys.argv[i] == "-?"):     # test for help flag
                    showUsage()          # show the help
                    sys.exit()         # exit
                elif (sys.argv[i] == "--help"):
                    showUsage()
                    sys.exit()
                elif (sys.argv[i] == "-h"):
                    showUsage()
                    sys.exit()
                elif (sys.argv[i][0] == "-"):
                    print "Error!  Unknown option.  Aborting"
                    sys.exit()
            else:                  # get the input file name
                inputfile = sys.argv[i]


# printConfig
# Debugging routine to print the parsed configuration file
# input: none
# output: configuration data printed to console
def printConfig():
    global config
    print >> sys.stderr, "Config ---------------------------------------------"
    list = config.sections()
    for i in range(len(list)):
        print >> sys.stderr
        print >> sys.stderr, list[i]
        for x in config.options(list[i]):
            if (x != "name") and (x != "__name__"):
                print >> sys.stderr, x, ":", config.get(list[i], x)
    print >> sys.stderr, "----------------------------------------------------"
    print >> sys.stderr

###########################################################################
# low-level outline processing functions


# indentLevel
# get the level of the line specified by linenum
# input: line
# output: returns the level number, 1 is the lowest
def indentLevel(line):
    strstart = line.lstrip()    # find the start of text in line
    x = line.find(strstart)     # find the text index in the line
    n = line.count("\t", 0, x)      # count the tabs
    n = n + line.count(" ", 0, x)     # count the spaces
    return(n + 1)         # return the count + 1 (for level)


# stripMarker
# return a line without its marker and leading and trailing whitespace
# input: line, marker
# output: stripped line
def stripMarker(line, marker):
    return line.lstrip(marker).strip()


# getLineType
# return the type of the line specified by linenum
# input: line
# output: returns text, usertext, table, preftext, etc.
def getLineType(line):
    if (line[0] == ':'):
        return 'text'
    elif (line[0] == ';'):
        return 'preftext'
    elif (line[0] == '>'):
        return 'usertext'
    elif (line[0] == '<'):
        return 'userpreftext'
    elif (line[0] == '|'):
        return 'table'
    elif (line[0] == '-'):
        return 'bulletheading'
    elif (line[0] == '+'):
        return 'numberheading'
# elif (line[0] == '['):
#    return 'checkboxheading'
    elif (line[0] == ''):
        return 'blank'
    else:
        return 'heading'


# getChildren
# return a list of line numbers for children of the passed line number
# input: linenum
# output: a (possibly) empty list of children
def getChildren(linenum):
    global outline, linecount

    children = []
    mylevel = outline[linenum][1]
    childlevel = mylevel + 1
    linenum = linenum + 1
    while (linenum < linecount) and (outline[linenum][1] > mylevel):
        if (outline[linenum][1] == childlevel):
            children.append(linenum)
        linenum = linenum + 1
    return children


# subTags
# substitute variables in output expressions
# input: section - section from config
# input: type - object type (to look up in config)
# input:  - substitution item (by name) from config array
# output: string - the substitution expression with variables inserted
def subTags(section, type):
    global config, v, parents

    varlist = v.keys()
    pattern = config.get(section, type)
    if len(parents) > 0:
        v["%p"] = str(parents[len(parents) - 1])

    for var in varlist:
        x = ""
        x = var
        y = ""
        y = v.get(var)
        pattern = re.sub(x, y, pattern)
    return pattern


#getBlock
#return a list of lines that match a mark (like : or ;)
#input: line number
#output: list of stripped lines
def getBlock(linenum, marker):
    global outline, linecount

    lines = []
    line = outline[linenum][0]
    while line[0] == marker:
        lines.append(stripMarker(line, marker))
        linenum = linenum + 1
        if linenum == linecount:
            break
        line = outline[linenum][0]
    return lines


#getUnstrippedBlock
#return a list of lines that match a mark (like : or ;)
#input: line number
#output: list of stripped lines
def getUnstrippedBlock(linenum, marker):
    global outline, linecount

    lines = []
    line = outline[linenum][0]
    while line[0] == marker:
        lines.append(line)
        linenum = linenum + 1
        if linenum == linecount:
            break
        line = outline[linenum][0]
    return lines

###########################################################################
# embedded object processing functions


# buildEscapes
# construct the dictionary for escaping special characters
# intput: config:escapes
# output: filled escapes dictionary
def buildEscapes():
    escapes = config.get("Document", "escapes")
    if len(escapes):
        list = escapes.split(" ")
        for pair in list:
            key, value = pair.split(",")
            escapeDict[key] = value


# charEscape
# escape special characters
# input: line
# output: modified line
def charEscape(line):
    return "".join(escapeDict.get(c, c) for c in line)


# getURL
# if there is a url, [url text], return the extracted link, url and value
# input: line
# output: link, url, text
def getURL(line):
    tags = []
    for tag in line.split("]"):
        tags.append(tag.split("["))

    for tag in tags:
        if len(tag) > 1 and re.search(" ", tag[1]):
            link = tag[1]

            url, text = link.split(" ", 1)
            link = "[" + tag[1] + "]"
            return link, url, text

#        return link.group(0), url, text
#    else:
#        return None, None, None
    return None, None, None


def handleURL(line):
    link, url, text = getURL(line)
    if link is None:
        return re.replace(line, "[url]", "")

    v["%u"] = url
    v["%v"] = text

    text = subTags("URLs", "url")
    line = re.replace(line, link, text)

    url = subTags("URLs", "url-attr")
    line = re.replace(line, "[url]", url)

    return line


###########################################################################
# outline header processing functions


# all outline object processors accept and output the following:
# input: linenum, enum
# output: print the output for each object
def handleHeading(linenum, enum):
    global outline, parents

    line = outline[linenum][0]

# url handling
# extract url data from line
# replace url object in line
# subTags line
# replace url attribute marker

    v["%%"] = line
    v["%l"] = str(outline[linenum][1])
    v["%n"] = str(linenum)
    v["%c"] = str(enum)
    children = getChildren(linenum)
    if enum == 1:
        output.append(subTags("Headings", "before-headings"))
    if children:
        output.append(subTags("Headings", "branch-heading"))
        parents.append([linenum, enum])
        handleObjects(children)
        parents.pop()
        output.append(subTags("Headings", "after-headings"))
    else:
        output.append(subTags("Headings", "leaf-heading"))


def handleBulleted(linenum, enum):
    global outline, parents

    v["%%"] = outline[linenum][0]
    v["%l"] = str(outline[linenum][1])
    v["%n"] = str(linenum)
    v["%c"] = str(enum)
    children = getChildren(linenum)
    if enum == 1:
        output.append(subTags("Headings", "before-bulleted-headings"))
    if children:
        output.append(subTags("Headings", "bulleted-branch-heading"))
        parents.append([linenum, enum])
        handleObjects(children)
        parents.pop()
        output.append(subTags("Headings", "after-bulleted-headings"))
    else:
        output.append(subTags("Headings", "bulleted-leaf-heading"))


def handleNumbered(linenum, enum):
    global outline, parents

    v["%%"] = outline[linenum][0]
    v["%l"] = str(outline[linenum][1])
    v["%n"] = str(linenum)
    v["%c"] = str(enum)
    children = getChildren(linenum)
    if enum == 1:
        output.append(subTags("Headings", "before-numbered-headings"))
    if children:
        output.append(subTags("Headings", "numbered-branch-heading"))
        parents.append([linenum, enum])
        handleObjects(children)
        parents.pop()
        output.append(subTags("Headings", "after-numbered-headings"))
    else:
        output.append(subTags("Headings", "numbered-leaf-heading"))

###########################################################################
# outline text block processing functions


# all outline object processors accept and output the following:
# input: linenum, enum
# output: print the output for each object
def handleText(linenum, enum):
    global outline, parents

    if enum != 1:
        return  # only execute for first call

    v["%l"] = str(outline[linenum][1])
    v["%n"] = str(linenum)
    v["%c"] = str(enum)
    list = getBlock(linenum, ':')
    output.append(subTags("Text", "before"))
    lines = ""
    for line in list:
        if line == "":
            lines = lines + config.get("Text", "paragraph-sep")
        else:
            lines = lines + line + config.get("Text", "line-sep")
    v["%%"] = lines
    output.append(subTags("Text", "text"))
    output.append(subTags("Text", "after"))


def handleUserText(linenum, enum):
    global outline, parents

    if enum != 1:
        return  # only execute for first call

    v["%l"] = str(outline[linenum][1])
    v["%n"] = str(linenum)
    v["%c"] = str(enum)
    list = getBlock(linenum, '>')
    output.append(subTags("UserText", "before"))
    lines = ""
    for line in list:
        if line == "":
            lines = lines + config.get("UserText", "paragraph-sep")
        else:
            lines = lines + line + config.get("UserText", "line-sep")
    v["%%"] = lines.strip()  # remove a possible extra separator
    output.append(subTags("UserText", "text"))
    output.append(subTags("UserText", "after"))


def handlePrefText(linenum, enum):
    global outline, parents

    if enum != 1:
        return  # only execute for first call

    v["%l"] = str(outline[linenum][1])
    v["%n"] = str(linenum)
    v["%c"] = str(enum)
    list = getBlock(linenum, ';')
    output.append(subTags("PrefText", "before"))
    lines = ""
    for line in list:
        if line == "":
            lines = lines + config.get("PrefText", "paragraph-sep")
        else:
            lines = lines + line + config.get("PrefText", "line-sep")
    v["%%"] = lines.strip()  # remove a possible extra separator
    output.append(subTags("PrefText", "text"))
    output.append(subTags("PrefText", "after"))


def handleUserPrefText(linenum, enum):
    global outline, parents

    if enum != 1:
        return  # only execute for first call

    v["%l"] = str(outline[linenum][1])
    v["%n"] = str(linenum)
    v["%c"] = str(enum)
    list = getBlock(linenum, '<')
    output.append(subTags("UserPrefText", "before"))
    lines = ""
    for line in list:
        if line == "":
            lines = lines + config.get("UserPrefText", "paragraph-sep")
        else:
            lines = lines + line + config.get("UserPrefText", "line-sep")
    v["%%"] = lines.strip()  # remove a possible extra separator
    output.append(subTags("UserPrefText", "text"))
    output.append(subTags("UserPrefText", "after"))

###########################################################################
# outline table processing functions


# isAlignRight
# return flag
# input: col, a string
def isAlignRight(col):
    l = len(col)
    if (col[0:2] == "  ") and (col[l - 2:l] != "  "):
        return 1
    else:
        return 0


# isAlignLeft
# return flag
# input: col, a string
def isAlignLeft(col):
    l = len(col)
    if (col[0:2] != "  ") and (col[l - 2:l] == "  "):
        return 1
    else:
        return 0


# isAlignCenter
# return flag
# input: col, a string
def isAlignCenter(col):
    l = len(col)
    if (col[0:2] == "  ") and (col[l - 2:l] == "  "):
        return 1
    else:
        return 0


# handleHeaderRow
# process a non-header table row
# input: row
# output: print the output for each object
def handleHeaderRow(row):
    global outline, parents

    row = row.rstrip("|").lstrip("|")
    columns = row.split("|")
    output.append(subTags("Tables", "before-table-header"))
    for col in columns:
        v["%%"] = col.strip()
        if isAlignCenter:
            output.append(subTags("Tables", "table-header-column-center"))
        elif isAlignCenter:
            output.append(subTags("Tables", "table-header-column-center"))
        elif isAlignCenter:
            output.append(subTags("Tables", "table-header-column-center"))
        else:
            output.append(subTags("Tables", "table-header-column"))
    output.append(subTags("Tables", "after-table-header"))


# handleRow
# process a non-header table row
# input: row
# output: print the output for each object
def handleRow(row):
    global outline, parents

    if row[0:2] == "||":
        handleHeaderRow(row)
        return
    row = row.rstrip("|").lstrip("|")
    columns = row.split("|")
    output.append(subTags("Tables", "before-table-row"))
    for col in columns:
        v["%%"] = col.strip()
        if isAlignCenter:
            output.append(subTags("Tables", "table-column-center"))
        elif isAlignLeft:
            output.append(subTags("Tables", "table-column-left"))
        elif isAlignRight:
            output.append(subTags("Tables", "table-column-right"))
        else:
            output.append(subTags("Tables", "table-column"))
    output.append(subTags("Tables", "after-table-row"))


# handleTable
# process a table
# input: linenum, enum
# output: print the output for each object
def handleTable(linenum, enum):
    global outline, parents

    if enum != 1:
        return  # only execute for first call

    v["%l"] = str(outline[linenum][1])
    v["%n"] = str(linenum)
    v["%c"] = str(enum)
    list = getUnstrippedBlock(linenum, '|')
    output.append(subTags("Tables", "before"))
    for row in list:
        handleRow(row)
    output.append(subTags("Tables", "after"))

###########################################################################
# outline wrapper processing functions


# addPreamble
# create the 'header' for the output document
# input: globals
# output: standard out
def addPreamble():
    global outline, v

    v["%%"] = ""
    output.append(subTags("Document", "preamble"))


# addPostamble
# create the 'header' for the output document
# input: globals
# output: standard out
def addPostamble():
    global outline, v

    v["%%"] = ""
    output.append(subTags("Document", "postamble"))


###########################################################################
# outline tree fuctions


# handleObject
# take an object and invoke the appropriate fuction to precess it
# input: linenum, enum (enum is the child order number of a parent)
# output: print the output of a object
def handleObject(linenum, enum):
    global outline, linecount

    obj = getLineType(outline[linenum][0])
    if obj == 'heading':
        handleHeading(linenum, enum)
    elif obj == 'bulled':
        handleBulleted(linenum, enum)
    elif obj == 'numbered':
        handleNumbered(linenum, enum)
    elif obj == 'text':
        handleText(linenum, enum)
    elif obj == 'usertext':
        handleUserText(linenum, enum)
    elif obj == 'preftext':
        handlePrefText(linenum, enum)
    elif obj == 'userpreftext':
        handleUserPrefText(linenum, enum)
    elif obj == 'table':
        handleTable(linenum, enum)
    else:
        print
        print "Error: unknown line type @ ", linenum
        sys.exit(1)


# handleObjects
# take an object list and invoke the appropriate fuctions to precess it
# input: linenum
# output: print the output of a object
def handleObjects(objs):
    for i in range(len(objs)):
        handleObject(objs[i], i + 1)

###########################################################################
# file functions


# readFile
# read the selected file into lines[]
# input: filename to be loaded
# output: a loaded-up lines[]
def readFile(inputfile):
    global outline, linecount, config
    file = open(inputfile, "r")
    linein = file.readline()

    while linein != "":
        indent = indentLevel(linein)
        line = charEscape(linein.strip())
        outline.append([line, indent])
        linein = file.readline()

    file.close

    outline[0][1] = 0  # set the first line to level 0

    linecount = len(outline)

###########################################################################
# Main Program Loop


def main():
    global outline, inputfile, linecount

    # get the arguments
    getArgs()

    # constuct the escapes dictionary
    buildEscapes()

    # read the input file
    readFile(inputfile)

    # get the title
    v["%t"] = outline[0][0].strip()

    # construct the initial data
    # parsing headings, text and tables
    # but not parsing links or images
    addPreamble()
    if config.get("Document", "first-is-node") == "true":
        objs = [0]
    else:
        objs = getChildren(0)
    handleObjects(objs)
    addPostamble()

    # handle embeded objects
    # parsing and constructing links, images and other embedded objects
    for i in range(len(output)):
        output[i] = handleURL(output[i])

    # output the final data
    for line in output:
        if line.strip() != "":
            print line.strip()

main()
