"""This module applies prototypes to each useful function of libpnd, and exports those functions with names that are more sane for Python usage (drops the "pnd_").

This will hopefully eventually be folded into LukeVP's libpnd wrapper."""

import ctypes as c

p = c.CDLL('libpnd.so.1')


#libc has at least one function needed to interact with libpnd.
libc = c.CDLL('libc.so.6')

FILE = c.c_void_p

libc.fopen.argtypes = [c.c_char_p, c.c_char_p]
libc.fopen.restype = FILE


#Data structures defined in libpnd.
#Many of these are defined as black-box types (void pointers).

##pnd_conf
conf_handle = c.c_void_p

##pnd_container
box_handle = c.c_void_p
box_node_t = c.c_void_p

##pnd_pxml
pxml_handle = c.c_void_p

##other...
# In both pnd_discovery.c and pnd_utility.c, it's apparently assumed that no
# PXML will be longer than 32 KiB.
PXML_MAXLEN = 32 * 1024


#Function prototypes.

##pnd_apps
get_appdata_path = p.pnd_get_appdata_path
get_appdata_path.argtypes = [c.c_char_p, c.c_char_p, c.c_char_p, c.c_uint]
get_appdata_path.restype = c.c_ubyte

##pnd_conf
conf_query_searchpath = p.pnd_conf_query_searchpath
conf_query_searchpath.argtypes = []
conf_query_searchpath.restype = c.c_char_p

conf_fetch_by_name = p.pnd_conf_fetch_by_name 
conf_fetch_by_name.argtypes = [c.c_char_p, c.c_char_p]
conf_fetch_by_name.restype = conf_handle

conf_get_as_char = p.pnd_conf_get_as_char
conf_get_as_char.argtypes = [conf_handle, c.c_char_p]
conf_get_as_char.restype = c.c_char_p

conf_get_as_int = p.pnd_conf_get_as_int
conf_get_as_int.argtypes = [conf_handle, c.c_char_p]
conf_get_as_int.restype = conf_handle

conf_get_as_int_d = p.pnd_conf_get_as_int_d
conf_get_as_int_d.argtypes = [conf_handle, c.c_char_p]
conf_get_as_int_d.restype = conf_handle

##pnd_container
box_get_name = p.pnd_box_get_name
box_get_name.argtypes = [box_handle]
box_get_name.restype = c.c_char_p

box_get_head = p.pnd_box_get_head
box_get_head.argtypes = [box_handle]
box_get_head.restype = box_node_t

box_get_key = p.pnd_box_get_key
box_get_key.argtypes = [box_node_t]
box_get_key.restype = c.c_char_p

box_get_next = p.pnd_box_get_next
box_get_next.argtypes = [box_node_t]
box_get_next.restype = box_node_t

box_get_size = p.pnd_box_get_size
box_get_size.argtypes = [box_handle]
box_get_size.restype = c.c_int

##pnd_discovery
disco_search = p.pnd_disco_search
disco_search.argtypes = [c.c_char_p, c.c_char_p]
disco_search.restype = box_handle

disco_file = p.pnd_disco_file
disco_file.argtypes = [c.c_char_p, c.c_char_p]
disco_file.restype = box_handle

##pnd_pndfiles
pnd_seek_pxml = p.pnd_pnd_seek_pxml
pnd_seek_pxml.argtypes = [FILE]
pnd_seek_pxml.restype = c.c_ubyte

pnd_accrue_pxml = p.pnd_pnd_accrue_pxml
pnd_accrue_pxml.argtypes = [FILE, c.c_char_p, c.c_uint]
pnd_accrue_pxml.restype = c.c_ubyte

##pnd_pxml
pxml_fetch = p.pnd_pxml_fetch
pxml_fetch.argtypes = [c.c_char_p]
pxml_fetch.restype = pxml_handle

pxml_delete = p.pnd_pxml_delete
pxml_delete.argtypes = [pxml_handle]
pxml_delete.restype = None

pxml_get_app_name_en = p.pnd_pxml_get_app_name_en
pxml_get_app_name_en.argtypes = [pxml_handle]
pxml_get_app_name_en.restype = c.c_char_p

pxml_get_app_name_de = p.pnd_pxml_get_app_name_de
pxml_get_app_name_de.argtypes = [pxml_handle]
pxml_get_app_name_de.restype = c.c_char_p

pxml_get_app_name_it = p.pnd_pxml_get_app_name_it
pxml_get_app_name_it.argtypes = [pxml_handle]
pxml_get_app_name_it.restype = c.c_char_p

pxml_get_app_name_fr = p.pnd_pxml_get_app_name_fr
pxml_get_app_name_fr.argtypes = [pxml_handle]
pxml_get_app_name_fr.restype = c.c_char_p

pxml_get_app_name = p.pnd_pxml_get_app_name
pxml_get_app_name.argtypes = [pxml_handle, c.c_char_p]
pxml_get_app_name.restype = c.c_char_p

pxml_get_unique_id = p.pnd_pxml_get_unique_id
pxml_get_unique_id.argtypes = [pxml_handle]
pxml_get_unique_id.restype = c.c_char_p

pxml_get_appdata_dirname = p.pnd_pxml_get_appdata_dirname
pxml_get_appdata_dirname.argtypes = [pxml_handle]
pxml_get_appdata_dirname.restype = c.c_char_p

pxml_get_standalone = p.pnd_pxml_get_standalone
pxml_get_standalone.argtypes = [pxml_handle]
pxml_get_standalone.restype = c.c_char_p

pxml_get_icon = p.pnd_pxml_get_icon
pxml_get_icon.argtypes = [pxml_handle]
pxml_get_icon.restype = c.c_char_p

pxml_get_description_en = p.pnd_pxml_get_description_en
pxml_get_description_en.argtypes = [pxml_handle]
pxml_get_description_en.restype = c.c_char_p

pxml_get_description_de = p.pnd_pxml_get_description_de
pxml_get_description_de.argtypes = [pxml_handle]
pxml_get_description_de.restype = c.c_char_p

pxml_get_description_it = p.pnd_pxml_get_description_it
pxml_get_description_it.argtypes = [pxml_handle]
pxml_get_description_it.restype = c.c_char_p

pxml_get_description_fr = p.pnd_pxml_get_description_fr
pxml_get_description_fr.argtypes = [pxml_handle]
pxml_get_description_fr.restype = c.c_char_p

pxml_get_description = p.pnd_pxml_get_description
pxml_get_description.argtypes = [pxml_handle, c.c_char_p]
pxml_get_description.restype = c.c_char_p

pxml_get_previewpic1 = p.pnd_pxml_get_previewpic1
pxml_get_previewpic1.argtypes = [pxml_handle]
pxml_get_previewpic1.restype = c.c_char_p

pxml_get_previewpic2 = p.pnd_pxml_get_previewpic2
pxml_get_previewpic2.argtypes = [pxml_handle]
pxml_get_previewpic2.restype = c.c_char_p

pxml_get_author_name = p.pnd_pxml_get_author_name
pxml_get_author_name.argtypes = [pxml_handle]
pxml_get_author_name.restype = c.c_char_p

pxml_get_author_website = p.pnd_pxml_get_author_website
pxml_get_author_website.argtypes = [pxml_handle]
pxml_get_author_website.restype = c.c_char_p

pxml_get_version_major = p.pnd_pxml_get_version_major
pxml_get_version_major.argtypes = [pxml_handle]
pxml_get_version_major.restype = c.c_char_p

pxml_get_version_minor = p.pnd_pxml_get_version_minor
pxml_get_version_minor.argtypes = [pxml_handle]
pxml_get_version_minor.restype = c.c_char_p

pxml_get_version_release = p.pnd_pxml_get_version_release
pxml_get_version_release.argtypes = [pxml_handle]
pxml_get_version_release.restype = c.c_char_p

pxml_get_version_build = p.pnd_pxml_get_version_build
pxml_get_version_build.argtypes = [pxml_handle]
pxml_get_version_build.restype = c.c_char_p

pxml_get_exec = p.pnd_pxml_get_exec
pxml_get_exec.argtypes = [pxml_handle]
pxml_get_exec.restype = c.c_char_p

pxml_get_execargs = p.pnd_pxml_get_execargs
pxml_get_execargs.argtypes = [pxml_handle]
pxml_get_execargs.restype = c.c_char_p

pxml_get_exec_option_no_x11 = p.pnd_pxml_get_exec_option_no_x11
pxml_get_exec_option_no_x11.argtypes = [pxml_handle]
pxml_get_exec_option_no_x11.restype = c.c_char_p

pxml_get_main_category = p.pnd_pxml_get_main_category
pxml_get_main_category.argtypes = [pxml_handle]
pxml_get_main_category.restype = c.c_char_p

pxml_get_subcategory1 = p.pnd_pxml_get_subcategory1
pxml_get_subcategory1.argtypes = [pxml_handle]
pxml_get_subcategory1.restype = c.c_char_p

pxml_get_subcategory2 = p.pnd_pxml_get_subcategory2
pxml_get_subcategory2.argtypes = [pxml_handle]
pxml_get_subcategory2.restype = c.c_char_p

pxml_get_altcategory = p.pnd_pxml_get_altcategory
pxml_get_altcategory.argtypes = [pxml_handle]
pxml_get_altcategory.restype = c.c_char_p

pxml_get_altsubcategory1 = p.pnd_pxml_get_altsubcategory1
pxml_get_altsubcategory1.argtypes = [pxml_handle]
pxml_get_altsubcategory1.restype = c.c_char_p

pxml_get_altsubcategory2 = p.pnd_pxml_get_altsubcategory2
pxml_get_altsubcategory2.argtypes = [pxml_handle]
pxml_get_altsubcategory2.restype = c.c_char_p

pxml_get_osversion_major = p.pnd_pxml_get_osversion_major
pxml_get_osversion_major.argtypes = [pxml_handle]
pxml_get_osversion_major.restype = c.c_char_p

pxml_get_osversion_minor = p.pnd_pxml_get_osversion_minor
pxml_get_osversion_minor.argtypes = [pxml_handle]
pxml_get_osversion_minor.restype = c.c_char_p

pxml_get_osversion_release = p.pnd_pxml_get_osversion_release
pxml_get_osversion_release.argtypes = [pxml_handle]
pxml_get_osversion_release.restype = c.c_char_p

pxml_get_osversion_build = p.pnd_pxml_get_osversion_build
pxml_get_osversion_build.argtypes = [pxml_handle]
pxml_get_osversion_build.restype = c.c_char_p

pxml_get_associationitem1_name = p.pnd_pxml_get_associationitem1_name
pxml_get_associationitem1_name.argtypes = [pxml_handle]
pxml_get_associationitem1_name.restype = c.c_char_p

pxml_get_associationitem1_filetype = p.pnd_pxml_get_associationitem1_filetype
pxml_get_associationitem1_filetype.argtypes = [pxml_handle]
pxml_get_associationitem1_filetype.restype = c.c_char_p

pxml_get_associationitem1_parameter = p.pnd_pxml_get_associationitem1_parameter
pxml_get_associationitem1_parameter.argtypes = [pxml_handle]
pxml_get_associationitem1_parameter.restype = c.c_char_p

pxml_get_associationitem2_name = p.pnd_pxml_get_associationitem2_name
pxml_get_associationitem2_name.argtypes = [pxml_handle]
pxml_get_associationitem2_name.restype = c.c_char_p

pxml_get_associationitem2_filetype = p.pnd_pxml_get_associationitem2_filetype
pxml_get_associationitem2_filetype.argtypes = [pxml_handle]
pxml_get_associationitem2_filetype.restype = c.c_char_p

pxml_get_associationitem2_parameter = p.pnd_pxml_get_associationitem2_parameter
pxml_get_associationitem2_parameter.argtypes = [pxml_handle]
pxml_get_associationitem2_parameter.restype = c.c_char_p

pxml_get_associationitem3_name = p.pnd_pxml_get_associationitem3_name
pxml_get_associationitem3_name.argtypes = [pxml_handle]
pxml_get_associationitem3_name.restype = c.c_char_p

pxml_get_associationitem3_filetype = p.pnd_pxml_get_associationitem3_filetype
pxml_get_associationitem3_filetype.argtypes = [pxml_handle]
pxml_get_associationitem3_filetype.restype = c.c_char_p

pxml_get_associationitem3_parameter = p.pnd_pxml_get_associationitem3_parameter
pxml_get_associationitem3_parameter.argtypes = [pxml_handle]
pxml_get_associationitem3_parameter.restype = c.c_char_p

pxml_get_clockspeed = p.pnd_pxml_get_clockspeed
pxml_get_clockspeed.argtypes = [pxml_handle]
pxml_get_clockspeed.restype = c.c_char_p

pxml_get_background = p.pnd_pxml_get_background
pxml_get_background.argtypes = [pxml_handle]
pxml_get_background.restype = c.c_char_p

pxml_get_mkdir = p.pnd_pxml_get_mkdir
pxml_get_mkdir.argtypes = [pxml_handle]
pxml_get_mkdir.restype = c.c_char_p

pxml_get_info_name = p.pnd_pxml_get_info_name
pxml_get_info_name.argtypes = [pxml_handle]
pxml_get_info_name.restype = c.c_char_p

pxml_get_info_type = p.pnd_pxml_get_info_type
pxml_get_info_type.argtypes = [pxml_handle]
pxml_get_info_type.restype = c.c_char_p

pxml_get_info_src = p.pnd_pxml_get_info_src
pxml_get_info_src.argtypes = [pxml_handle]
pxml_get_info_src.restype = c.c_char_p

##pnd_utility
pxml_get_by_path = p.pnd_pxml_get_by_path
pxml_get_by_path.argtypes = [c.c_char_p]
#It actually returns an array.  Not sure why POINTER makes it work.
#Note that what gets returned needs to be iterated over, with the results
#passed to the pnd_pxml functions.
pxml_get_by_path.restype = c.POINTER(pxml_handle)
