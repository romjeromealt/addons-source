# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2009        Brian G. Matherly
# Copyright (C) 2010        Douglas S. Blank
# Copyright (C) 2011-2012   Jerome Rapinat
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import sys
import os
from shutil import copy
from gi.repository import Gtk
import logging

# GRAMPS modules
from gramps.gen.plug import Gramplet
from gramps.gen.lib import date
import gramps.gen.datehandler
from gramps.gen.const import USER_HOME, USER_PLUGINS
from gramps.gen.config import config
from gramps.gui.display import display_url
from gramps.gui.dialog import ErrorDialog
from gramps.plugins.lib.libhtml import Html, xml_lang
from gramps.gen.const import GRAMPS_LOCALE as glocale

try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext

LOG = logging.getLogger("lxml")

# Try to detect the presence of gzip
try:
    import gzip
    GZIP_OK = True
except ImportError:
    GZIP_OK = False
    ErrorDialog(_('Where is gzip?'), _('"gzip" is missing'))
    LOG.error('No gzip')

# Try to detect the presence of lxml (only for using XPATH/XSLT)
try:
    from lxml import etree, objectify
    LXML_OK = True
    LXML_VERSION = etree.LXML_VERSION
    LIBXML_VERSION = etree.LIBXML_VERSION
    LIBXSLT_VERSION = etree.LIBXSLT_VERSION
except ImportError:
    LXML_OK = False
    ErrorDialog(_('Missing python3 lxml'), _('Please, try to install "python3 lxml" package.'))
    LOG.error('No lxml')

# Timestamp converter
def epoch(t):
    """
    Convert a timestamp to a human-readable date format.
    """
    try:
        from datetime import datetime
    except ImportError:
        LOG.error('Modules around time missing')
        return 'Unknown'

    if t is None:
        LOG.warning(_('Invalid timestamp'))
        return _('Unknown')

    date = int(t)
    conv = datetime.fromtimestamp(date)
    return conv.strftime('%d %B %Y')

NAMESPACE = '{http://gramps-project.org/xml/1.7.2/}'

class LxmlGramplet(Gramplet):
    """
    Gramplet for testing lxml.
    """

    def init(self):
        """
        Constructs the GUI, consisting of an entry, a text view, and a Run button.
        """
        self.__base_path = USER_HOME
        self.__file_name = "test.gramps"
        self.entry = Gtk.Entry()
        self.entry.set_text(os.path.join(self.__base_path, self.__file_name))

        self.button = Gtk.Button()
        image = Gtk.Image.new_from_icon_name(Gtk.STOCK_OPEN, Gtk.IconSize.BUTTON)
        self.button.add(image)
        self.button.connect('clicked', self.__select_file)

        vbox = Gtk.VBox()
        hbox = Gtk.HBox()

        self.import_text = Gtk.TextView()
        self.import_text.set_wrap_mode(Gtk.WrapMode.WORD)
        self.import_text.set_editable(False)

        self.text = Gtk.TextBuffer()
        self.text.set_text(_('No file loaded...'))
        self.import_text.set_buffer(self.text)

        vbox.pack_start(self.import_text, True, True, 0)
        button = Gtk.Button(_("Run"))
        button.connect("clicked", self.run)
        vbox.pack_start(button, False, False, 0)

        hbox.pack_start(self.entry, True, True, 0)
        hbox.pack_end(self.button, False, False, 0)

        vbox.pack_end(hbox, False, False, 0)

        self.gui.get_container_widget().remove(self.gui.textview)
        self.gui.get_container_widget().add_with_viewport(vbox)

        vbox.show_all()

    def __select_file(self, obj):
        """
        Callback function to handle the open button press.
        """
        dialog = Gtk.FileChooserDialog(
            title='lxml',
            action=Gtk.FileChooserAction.OPEN,
            buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        )

        dialog.set_current_name(os.path.basename(self.entry.get_text()))
        dialog.set_current_folder(self.__base_path)
        dialog.present()

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self.set_filename(dialog.get_filename())
        dialog.destroy()

    def set_filename(self, path):
        """
        Set the currently selected file.
        """
        if not path:
            return

        self.__base_path = os.path.dirname(path) or os.getcwd()
        self.__file_name = os.path.basename(path)
        self.entry.set_text(os.path.join(self.__base_path, self.__file_name))

    def run(self, obj):
        """
        Method that is run when you click the Run button.
        """
        entry = self.entry.get_text()
        if ' ' in entry:
            ErrorDialog(_('Space character in filename'), _('Please fix space in "%s"') % entry)
            LOG.error('Space on filename')
            return

        self.read_xml(entry)

    def read_xml(self, entry):
        """
        Read the .gramps file.
        """
        use_gzip = self.is_gzip(entry)

        if os.name not in ['posix', 'nt']:
            self.text.set_text(_('Sorry, no support for your OS yet!'))
            LOG.error('Not tested under this OS')
            return

        filename = os.path.join(USER_PLUGINS, 'lxml', 'test.xml')

        if LXML_OK and use_gzip:
            self.uncompress_file(entry, filename)
        elif LXML_OK:
            self.copy_file(entry, filename)
        else:
            LOG.error('lxml or gzip is missing')
            return

        self.validate_xml(filename, entry)

    def is_gzip(self, entry):
        """
        Check if the file is gzip compressed.
        """
        if GZIP_OK:
            try:
                with gzip.open(entry, "r") as test:
                    test.read(1)
                return True
            except (IOError, ValueError):
                return False
        return False

    def uncompress_file(self, entry, filename):
        """
        Uncompress the gzip file.
        """
        try:
            os.system(f'gunzip < {entry} > {filename}')
        except Exception as e:
            ErrorDialog(_('Is it a compressed .gramps?'), _('Cannot uncompress "%s"') % entry)
            LOG.error('Cannot use gunzip command')
            raise e

    def copy_file(self, entry, filename):
        """
        Copy the file to the destination.
        """
        try:
            copy(entry, filename)
        except Exception as e:
            ErrorDialog(_('Is it a .gramps?'), _('Cannot copy "%s"') % entry)
            LOG.error('Cannot copy the file')
            raise e

    def validate_xml(self, filename, entry):
        """
        Validate the XML file using XSD, DTD, and RNG.
        """
        xsd = os.path.join(USER_PLUGINS, 'lxml', 'grampsxml.xsd')
        try:
            self.xsd(xsd, filename)
        except Exception as e:
            ErrorDialog(_('XSD validation (lxml)'), _('Cannot validate "%(file)s"!') % {'file': entry})
            LOG.debug(e)
            return

        try:
            self.check_valid(filename)
        except Exception as e:
            LOG.info(_('xmllint: skip DTD validation for "%(file)s"') % {'file': entry})

        rng = os.path.join(USER_PLUGINS, 'lxml', 'grampsxml.rng')
        try:
            if os.name == 'nt':
                os.system(f'xmllint --relaxng {rng} --noout {filename}')
            else:
                os.system(f'xmllint --relaxng file://{rng} --noout {filename}')
        except Exception as e:
            LOG.info(_('xmllint: skip RelaxNG validation for "%(file)s"') % {'file': entry})

        try:
            tree = etree.parse(filename)
            doctype = tree.docinfo.doctype
            current = '<!DOCTYPE database PUBLIC "-//Gramps//DTD Gramps XML 1.7.2//EN" "http://gramps-project.org/xml/1.7.2/grampsxml.dtd">'
            if self.rng_validation(tree, rng):
                self.parse_xml(tree, filename)
            elif doctype != current:
                ErrorDialog(_('Gramps version'), _('Wrong namespace\nNeed: %s') % current)
                LOG.error('Namespace is wrong')
            else:
                ErrorDialog(_('RelaxNG validation'), _('Cannot validate "%(file)s" via RelaxNG schema') % {'file': entry})
                LOG.error('RelaxNG validation failed')
        except etree.XMLSyntaxError as e:
            ErrorDialog(_('File issue'), _('Cannot parse "%(file)s" via etree') % {'file': entry})
            log = e.error_log.filter_from_level(etree.ErrorLevels.FATAL)
            LOG.debug(log)
            debug = e.error_log.last_error
            LOG.debug(debug.domain_name)
            LOG.debug(debug.type_name)
            LOG.debug(debug.filename)

    def parse_xml(self, tree, filename):
        """
        Parse the validated .gramps file.
        """
        root = tree.getroot()

        if isinstance(self.text, list):
            pass
        else:
            self.text.set_text(_('Parsing file...'))

        namespace = root.nsmap
        surname_tag = etree.SubElement(root, NAMESPACE + 'surname')
        pname_tag = etree.SubElement(root, NAMESPACE + 'pname')
        private_surname = config.get('preferences.private-surname-text')
        private_record = config.get('preferences.private-record-text')

        expr = "//*[local-name() = $name]"
        count_elements = etree.XPath("count(//*[local-name() = $name])")
        desc = etree.XPath('descendant-or-self::text()')

        msg = []
        places = []
        sources = []
        surnames = []
        timestamp = []
        thumbs = []

        LOG.info('start iteration')

        for one in root.iter():
            for two in one.iter():
                msg.append(two.items())

                if two.tag == NAMESPACE + 'mediapath':
                    mediapath = two.text
                else:
                    mediapath = ''

                if two.get('priv'):
                    text = private_record
                else:
                    text = ""

                for three in two.iter():
                    if two.get('change'):
                        timestamp.append(two.get('change'))

                    if three.tag == NAMESPACE + 'ptitle':
                        if text != private_record:
                            text = str(three.text)
                        if text not in places:
                            places.append(text)

                    if three.tag == NAMESPACE + 'pname':
                        if text != private_record:
                            text = str(three.attrib.get('value'))
                        translation = str(three.attrib.get('lang'))
                        if translation == 'None':
                            translation = xml_lang()[0:2]
                            text = text + _(' - (? or %(lang)s)') % {'lang': translation}
                        else:
                            text = text + _(' - (%(lang)s)') % {'lang': translation}
                        if text not in places:
                            places.append(text)

                    if three.tag == NAMESPACE + 'stitle' and three.text not in sources:
                        sources.append(three.text or "")

                    if three.tag == NAMESPACE + 'file' and three.items() not in thumbs:
                        thumbs.append(three.items())

                    for four in three.iter():
                        if four.tag == NAMESPACE + 'surname' and four.text is not None:
                            if text != private_record:
                                surnames.append(four.text)
                            else:
                                surnames.append(private_surname)

        LOG.info('end of loops')

        log = msg[2]
        if not log:
            ErrorDialog(_('Missing header'), _('Not a valid .gramps.\n'
                                              'Cannot run the gramplet...\n'
                                              'Please, try to use a .gramps\n'
                                              'generated by Gramps 6.x.'))
            LOG.error('header missing')
            return

        if int(count_elements(root, name='surname')) > 1:
            nb_surnames = int(count_elements(root, name='surname'))
        else:
            nb_surnames = surnames = [_('0')]

        if int(count_elements(root, name='pname')) > 1:
            nb_pnames = int(count_elements(root, name='pname'))
        else:
            nb_pnames = places = [_('0')]

        if int(count_elements(root, name='note')) > 1:
            nb_notes = int(count_elements(root, name='note'))
        else:
            nb_notes = _('0')

        if int(count_elements(root, name='stitle')) > 1:
            nb_sources = int(count_elements(root, name='stitle'))
        else:
            nb_sources = _('0')

        timestamp.sort()
        start = timestamp[0]
        end = timestamp[-1]
        timestamp = []
        first = epoch(start)
        last = epoch(end)

        header = _('File parsed with') + ' LXML' + str(LXML_VERSION) + '\n\n'
        [(k1, v1), (k2, v2)] = log
        file_info = _('File was generated on ') + v1 + '\n\t' + _(' by Gramps ') + v2 + '\n\n'
        period = _('Period: ') + first + ' => ' + last + '\n\n'
        su = '\t' + str(nb_surnames) + '\t' + _(' entries for surname(s); no frequency yet') + '\n'
        p = '\t' + str(nb_pnames) + '\t' + _(' entries for place(s)') + '\n'
        n = '\t' + str(nb_notes) + '\t' + _(' note(s)') + '\n'
        so = '\t' + str(nb_sources) + '\t' + _(' source(s)') + '\n\n'
        counters = su + p + n + so
        libs = 'LIBXML' + str(LIBXML_VERSION) + '\tLIBXSLT' + str(LIBXSLT_VERSION)

        if isinstance(self.text, list):
            pass
        else:
            self.text.set_text(header + file_info + period + counters + libs)

        LOG.info('### NEW FILES ###')
        LOG.info('content parsed and copied')

        self.write_xml(log, first, last, surnames, places, sources)
        self.print_media(thumbs, mediapath)
        images = os.path.join(USER_PLUGINS, 'lxml', _('Gallery.html'))
        sys.stdout.write(_('2. Has generated a media index on "%(file)s".\n') % {'file': images})

        unique_surnames = list(set(surnames))
        unique_surnames.sort()

        self.write_back_xml(filename, root, unique_surnames, places, sources)
        sys.stdout.write(_('3. Has written entries into "%(file)s".\n') % {'file': filename})

    def xsd(self, xsd, filename):
        """
        Validate the XML file against the XSD schema.
        """
        schema = etree.XMLSchema(file=xsd)
        parser = objectify.makeparser(schema=schema)
        tree = etree.parse(filename)
        root = tree.getroot()
        objectify.fromstring(etree.tostring(root, encoding="UTF-8"), parser)
        LOG.info(_('Matches XSD schema.'))

    def check_valid(self, filename):
        """
        Validate the XML file against the DTD schema.
        """
        dtd = os.path.join(USER_PLUGINS, 'lxml', 'grampsxml.dtd')
        try:
            if os.name == 'nt':
                os.system(f'xmllint --dtdvalid {dtd} --noout --dropdtd {filename}')
            else:
                os.system(f'xmllint --dtdvalid file://{dtd} --noout --dropdtd {filename}')
        except Exception as e:
            LOG.info(_('xmllint: skip DTD validation'))

    def rng_validation(self, tree, rng):
        """
        Validate the XML file against the RNG schema.
        """
        valid = etree.ElementTree(file=rng)
        schema = etree.RelaxNG(valid)
        return schema.validate(tree)

    def write_xml(self, log, first, last, surnames, places, sources):
        """
        Write the result of the query for distributed, shared protocols.
        """
        self.lang = xml_lang()
        self.title = _('I am looking at ...')
        self.footer = _('Content generated by Gramps')
        self.surnames_title = _('Surnames')
        self.places_name = _('Places')
        self.sources_title = _('List of sources')
        time = date.Today()

        xml = etree.Element("query")
        xml.set("lang", self.lang)
        xml.set("title", self.title)
        xml.set("footer", self.footer)
        xml.set("date", gramps.gen.datehandler.displayer.display(time))
        xml.set("first", first)
        xml.set("last", last)

        doc = etree.ElementTree(xml)

        countries = [
            '', _('Australia'), _('Brazil'), _('Bulgaria'), _('Canada'), _('Chile'),
            _('China'), _('Croatia'), _('Czech Republic'), _('England'), _('Finland'),
            _('France'), _('Germany'), _('India'), _('Japan'), _('Norway'),
            _('Portugal'), _('Russia'), _('Sweden'), _('United States of America')
        ]

        c = etree.SubElement(xml, "clist")
        self.name = _('Name')
        self.country = _('Country')
        c.set("pname", self.name)
        c.set("country", self.country)
        for country in countries:
            c1 = etree.SubElement(c, "country")
            c1.text = country

        [(k1, v1), (k2, v2)] = log
        l = etree.SubElement(xml, "log")
        l.set("date", v1)
        l.set("version", v2)

        s = etree.SubElement(xml, "surnames")
        s.set("title", self.surnames_title)

        surnames.sort()
        cnt = []
        for surname in surnames:
            if surname not in cnt:
                s1 = etree.SubElement(s, "surname")
                s1.text = surname
                cnt.append(surname)

        p = etree.SubElement(xml, "places")
        p.set("pname", self.places_name)

        places.sort()
        for place in places:
            p1 = etree.SubElement(p, "place")
            p1.text = place

        src = etree.SubElement(xml, "sources")
        src.set("title", self.sources_title)

        sources.sort()
        for source in sources:
            src1 = etree.SubElement(src, "source")
            src1.text = source

        content = etree.XML(etree.tostring(xml, encoding="UTF-8"))

        xslt_doc = etree.parse(os.path.join(USER_PLUGINS, 'lxml', 'query_html.xsl'))
        transform = etree.XSLT(xslt_doc)
        outdoc = transform(content)
        html = os.path.join(USER_PLUGINS, 'lxml', 'query.html')
        with open(html, 'w') as outfile:
            outfile.write(str(outdoc))

        content.clear()

        sys.stdout.write(_('1. Has generated "%s".\n') % html)
        LOG.info(_('Try to open\n "%s"\n into your preferred web navigator ...') % html)
        display_url(html)

    def print_media(self, thumbs, mediapath):
        """
        Print some media infos via HTML class (Gramps).
        """
        LOG.info('Looking at media...')

        title = _('Gallery')
        fname = os.path.join(USER_PLUGINS, 'lxml', _('Gallery.html'))
        with open(fname, "w") as of:
            LOG.info('Empty "Gallery.html" file created')

            lang = xml_lang()
            page, head, body = Html.page(title, encoding='utf-8', lang=str(lang))
            head = body = ""

            self.text = []

            self.xhtml_writer(fname, page, head, body, of, thumbs, mediapath)

        LOG.info('End (Media)')

    def __write_gallery(self, thumbs, mediapath):
        """
        This procedure writes out the media.
        """
        LOG.info('Looking at gallery')

        from gramps.gen.utils.thumbnails import get_thumbnail_path

        fullclear = Html("div", class_="fullclear", inline=True)

        LOG.info('Start to enumerate for gallery')

        for thumb in thumbs:
            src = thumb.get('src', 'No src')
            mime = thumb.get('mime', 'No mime')
            checksum = thumb.get('checksum', 'No checksum')
            description = thumb.get('description', 'No description')

            src = os.path.join(mediapath, src)
            if not src.startswith("/"):
                src = os.path.join(USER_HOME, src)

            if mime.startswith("image"):
                thumb_path = get_thumbnail_path(str(src), mtype=None, rectangle=None)
                self.text += Html('img', src=str(thumb_path), mtype=str(mime))
                self.text += fullclear
                self.text += Html('a', str(description), href=str(src), target='blank', title=str(mime))
                self.text += fullclear

        return self.text

    def close_file(self, of):
        """Close the file."""
        of.close()

    def xhtml_writer(self, fname, page, head, body, of, thumbs, mediapath):
        """
        Format, write, and close the file.
        """
        self.__write_gallery(thumbs, mediapath)

        with open(fname, 'w') as text:
            text.write(head)
            for txt in self.text:
                text.write(txt + '\n')

        self.close_file(of)

        LOG.info('Gallery generated')

    def write_back_xml(self, filename, root, surnames, places, sources):
        """
        Write the result of the query back into the XML file (Gramps scheme).
        """
        with open(filename, 'w') as outfile:
            root.clear()
            the_id = 0

            people = etree.SubElement(root, "people")
            for s in surnames:
                the_id += 1
                person = etree.SubElement(people, "person")
                person.set('id', f'{the_id}_{len(surnames)}')
                name = etree.SubElement(person, "name")
                surname = etree.SubElement(name, "surname")
                surname.text = s

            pl = etree.SubElement(root, "places")
            for p in places:
                the_id += 1
                place = etree.SubElement(pl, "placeobj")
                place.set('id', f'{the_id}_{len(places)}')
                name = etree.SubElement(place, "pname")
                name.set('value', p)

            src = etree.SubElement(root, "sources")
            for s in sources:
                the_id += 1
                source = etree.SubElement(src, "source")
                source.set('id', f'{the_id}_{len(sources)}')
                stitle = etree.SubElement(source, "stitle")
                stitle.text = s

            out = etree.tostring(root, method='xml', pretty_print=True)
            str_out = out.decode('utf-8')
            outfile.write(str_out)

        root.clear()
