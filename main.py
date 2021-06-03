import os
import sys
import datetime
import tkinter as tk
from tkinter import filedialog, messagebox
import decimal
import xml.etree.ElementTree as ET
import pygubu
import configparser

PROJECT_PATH = os.path.abspath(getattr(sys, '_MEIPASS', os.path.dirname(__file__)))
PROJECT_UI = os.path.join(PROJECT_PATH, 'ksaow.ui')
PROJECT_APP_NAME = 'KsaowApp'

DEFAULT_READ_PATH = ''
DEFAULT_WRITE_PATH = ''

FILE_TYPES = [("Plik XML", ".xml")]
DECIMAL_ZERO = decimal.Decimal(0).quantize(decimal.Decimal('0.0001'))

CLCONST = datetime.date(1800, 12, 28)


def read_cfg():
    global DEFAULT_READ_PATH
    global DEFAULT_WRITE_PATH

    cfg_dir = os.path.expandvars('$APPDATA/Python'+PROJECT_APP_NAME)
    cfg_file = os.path.join(cfg_dir, 'config.ini')
    cfg = configparser.ConfigParser()
    if not os.path.isdir(cfg_dir):
        os.mkdir(cfg_dir)
    if os.path.isfile(cfg_file):
        cfg.read(cfg_file)
    else:
        # default configuration
        cfg['default'] = {'default_read_path': '.',
                          'default_write_path': '.'}

    DEFAULT_READ_PATH = cfg['default']['default_read_path']
    DEFAULT_WRITE_PATH = cfg['default']['default_write_path']


def save_cfg():
    global DEFAULT_READ_PATH
    global DEFAULT_WRITE_PATH

    cfg_dir = os.path.expandvars('$APPDATA/Python'+PROJECT_APP_NAME)
    cfg_file = os.path.join(cfg_dir, 'config.ini')
    cfg = configparser.ConfigParser()
    if not os.path.isdir(cfg_dir):
        os.mkdir(cfg_dir)

    cfg['default'] = {'default_read_path': DEFAULT_READ_PATH,
                      'default_write_path': DEFAULT_WRITE_PATH}
    with open(cfg_file, 'w') as configfile:
        cfg.write(configfile)


class KsaowVars(object):
    lbl_number_corr_docs = None
    lbl_number_purchase_docs = None
    lbl_number_all_docs = None
    lbl_number_contractors = None
    lbl_sum_brutto = None
    lbl_sum_vat = None
    lbl_sum_netto = None
    dest_path = None
    src_path = None
    cfg_purchase_invoice_corr = None
    cfg_purchase_invoice = None


class KsaowApp:
    def __init__(self):

        self.contractors = {}
        self.documents = {}

        self.src_program_name = ''
        self.src_program_ver = ''
        self.src_import_time = ''

        self.builder = builder = pygubu.Builder()
        builder.add_resource_path(PROJECT_PATH)
        builder.add_from_file(PROJECT_UI)
        self.mainwindow = builder.get_object('mainwindow')
        builder.connect_callbacks(self)

        self.btn_save_as = self.builder.get_object('btn_save_as')
        self.btn_save = self.builder.get_object('btn_save')
        self.treeview_contractors = self.builder.get_object('treeview_contractors')
        self.treeview_docs = self.builder.get_object('treeview_docs')

        self.builder.import_variables(KsaowVars)

        KsaowVars.cfg_purchase_invoice.set(True)
        KsaowVars.cfg_purchase_invoice_corr.set(True)

    def get_src_file(self):
        global DEFAULT_READ_PATH
        src_filename = filedialog.askopenfilename(title="Plik do wczytania", filetypes=FILE_TYPES,
                                                  initialdir=DEFAULT_READ_PATH)
        if src_filename:
            KsaowVars.src_path.set(src_filename)
            DEFAULT_READ_PATH = os.path.dirname(src_filename)
            try:
                self.parse_file(src_filename)
                self.btn_save_as['state'] = tk.NORMAL
            except:
                messagebox.showwarning('Błąd!', 'Otworzenie pliku {} nie powiodło się. '.format(src_filename) +
                                       'Upewnij się, czy plik jest na pewno w dobrym formacie')
                self.btn_save_as['state'] = tk.DISABLED
                self.btn_save['state'] = tk.DISABLED

    def get_dest_file(self):
        global DEFAULT_WRITE_PATH
        dest_filename = filedialog.asksaveasfilename(title="Plik do zapisania", defaultextension="xml",
                                                     filetypes=FILE_TYPES,
                                                     initialdir=DEFAULT_WRITE_PATH)
        if dest_filename:
            KsaowVars.dest_path.set(dest_filename)
            DEFAULT_WRITE_PATH = os.path.dirname(dest_filename)
            self.btn_save['state'] = tk.NORMAL

    def close_app(self):
        self.mainwindow.destroy()

    def update_contractors_view(self):
        # populate treeview...

        self.treeview_contractors.delete(*self.treeview_contractors.get_children())

        for idx, entry in self.contractors.items():
            label = '{}'.format(idx)
            column_data = (entry['int_id'], entry['name'], entry['nip'],
                           '{} {}, {}'.format(entry['zip'], entry['city'], entry['address']))
            self.treeview_contractors.insert('', tk.END, text=label, values=column_data)

    def update_docs_view(self):

        tmp_sum = {'netto': decimal.Decimal(0),
                   'vat': decimal.Decimal(0),
                   'brutto': decimal.Decimal(0)}

        self.treeview_docs.delete(*self.treeview_docs.get_children())

        for idx, entry in self.documents.items():

            if KsaowVars.cfg_purchase_invoice.get() is False and entry['cor'] is False:
                continue
            if KsaowVars.cfg_purchase_invoice_corr.get() is False and entry['cor'] is True:
                continue

            label = '{}'.format(idx)
            column_data = (entry['cor'], entry['date_issue'], entry['doc_no'],
                           self.contractors[entry['id_ctr']]['name'], '',
                           entry['sum_netto'].quantize(decimal.Decimal('0.01')),
                           entry['sum_vat'].quantize(decimal.Decimal('0.01')),
                           entry['sum_brutto'].quantize(decimal.Decimal('0.01')))
            tmp_sum['netto'] += entry['sum_netto']
            tmp_sum['brutto'] += entry['sum_brutto']
            itemid = self.treeview_docs.insert('', tk.END, text=label, values=column_data)
            for id_vat, entry_vat in entry['vat'].items():
                label = ''
                column_data = ('', '', '', '', id_vat, entry_vat['netto'].quantize(decimal.Decimal('0.01')),
                               entry_vat['vat'].quantize(decimal.Decimal('0.01')),
                               entry_vat['brutto'].quantize(decimal.Decimal('0.01')))
                self.treeview_docs.insert(itemid, tk.END, text=label, values=column_data)
                tmp_sum['vat'] += entry_vat['vat']
        KsaowVars.lbl_sum_netto.set(tmp_sum['netto'].quantize(decimal.Decimal('0.01')))
        KsaowVars.lbl_sum_vat.set(tmp_sum['vat'].quantize(decimal.Decimal('0.01')))
        KsaowVars.lbl_sum_brutto.set(tmp_sum['brutto'].quantize(decimal.Decimal('0.01')))

    def parse_file(self, filename):

        # clear dictionaries

        self.contractors.clear()
        self.documents.clear()

        # open file...

        tree = ET.parse(filename)
        root = tree.getroot()

        # read basic info about program and time from file

        self.src_program_name = root.find('./info/symbol-systemu').text
        self.src_program_ver = root.find('./info/nazwa-systemu').text
        self.src_import_time = root.find('./info/data-czas-generacji').text

        # read all suppliers from file and put it into dictionary

        for item in root.findall('./kartoteki/kartoteka'):
            if 'DOST' not in item.find('wewn-ident').text:
                continue
            idx = item.attrib['lp']
            entry = {
                'int_id': item.find('./wewn-ident').text[4:],
                'name': item.find('./nazwa1').text,
                'nip': item.find("./nip").text,
                'zip': '' if item.find("./adres-telefon/kod-pocztowy") is None else item.find(
                    "./adres-telefon/kod-pocztowy").text,
                'city': '' if item.find("./adres-telefon/miejscowosc") is None else item.find(
                    "./adres-telefon/miejscowosc").text,
                'address': '' if item.find("./adres-telefon/adres") is None else
                                item.find("./adres-telefon/adres").text
            }
            self.contractors[idx] = entry
        KsaowVars.lbl_number_contractors.set(len(self.contractors))

        self.update_contractors_view()

        # read documents
        tmp_cor_no = 0
        tmp_docs_no = 0

        for item in root.findall('./dokument'):
            if item.find('./naglowek/rodzaj-dokumentu').text != 'Z':
                continue

            if item.find('./naglowek/czy-korekta').text == 'true':
                tmp_cor = True
                tmp_orig_doc_no = item.find('./naglowek-kor/nr-dokumentu-kor').text
                tmp_cor_no += 1
            else:
                tmp_cor = False
                tmp_orig_doc_no = ''
                tmp_docs_no += 1

            tmp_vat = {}
            for v_item in item.findall('./podsumowanie-fk/kwoty/kwota'):
                if v_item.find('./stawka-vat') is not None:
                    tmp_vat_id = v_item.find('./stawka-vat').text
                else:
                    tmp_vat_id = 'SUM'
                if tmp_vat_id not in tmp_vat:
                    tmp_vat[tmp_vat_id] = {'netto': DECIMAL_ZERO, 'vat': DECIMAL_ZERO, 'brutto': DECIMAL_ZERO}
                if 'kwd-netto-zakupu' in v_item.find('./symbol').text:
                    tmp_vat[tmp_vat_id]['netto'] = decimal.Decimal(v_item.find('./wartosc').text)\
                        .quantize(decimal.Decimal('0.0001'))
                elif 'kwd-vat-zakupu' in v_item.find('./symbol').text:
                    tmp_vat[tmp_vat_id]['vat'] = decimal.Decimal(v_item.find('./wartosc').text)\
                        .quantize(decimal.Decimal('0.0001'))
                elif 'kwd-brutto-zakupu' in v_item.find('./symbol').text:
                    tmp_vat[tmp_vat_id]['brutto'] = decimal.Decimal(v_item.find('./wartosc').text)\
                        .quantize(decimal.Decimal('0.0001'))
                else:
                    pass

            entry = {'int_id': item.find('./naglowek/wewn-ident').text[4:],
                     'full_id': item.find('./naglowek/wewn-ident').text,
                     'doc_no': item.find('./naglowek/nr-dokumentu').text,
                     'cor': tmp_cor,
                     'orig_doc_no': tmp_orig_doc_no,
                     'id_ctr': item.find('./naglowek/kontrahent').text,
                     'id_payer': item.find('./naglowek/sprzedawca').text,
                     'payment_type': item.find('./naglowek/forma-platnosci/symbol').text,
                     'date_issue': item.find('./naglowek/data-wystawienia').text,
                     'date_delivery': item.find('./naglowek/data-otrzymania').text,
                     'date_due': item.find('./naglowek/termin-platnosci/data').text,
                     'vat': tmp_vat,
                     'sum_netto': tmp_vat['SUM']['netto'],
                     'sum_vat': tmp_vat['SUM']['vat'],
                     'sum_brutto': tmp_vat['SUM']['brutto']
                     }
            del entry['vat']['SUM']

            self.documents[item.attrib['lp']] = entry
        KsaowVars.lbl_number_all_docs.set(len(self.documents))
        KsaowVars.lbl_number_purchase_docs.set(tmp_docs_no)
        KsaowVars.lbl_number_corr_docs.set(tmp_cor_no)

        self.update_docs_view()

    def save_file(self):
        filename = KsaowVars.dest_path.get()

        tmp_docs_no = 0  # we need to count number of documents we'd like to save
        # Prepare XML

        root = ET.Element("MAGIK_EKSPORT")

        # Podstawowa struktura

        info = ET.SubElement(root, "INFO_EKSPORTU")
        dokumenty = ET.SubElement(root, "DOKUMENTY")
        kontrahenci = ET.SubElement(root, "KARTOTEKA_KONTRAHENTOW")
        ET.SubElement(root, "KARTOTEKA_PRACOWNIKOW")
        ET.SubElement(root, "KARTOTEKA_ARTYKULOW")

        ET.SubElement(info, "WERSJA_MAGIKA").text = "4.2.0"
        ET.SubElement(info, "NAZWA_PROGRAMU").text = self.src_program_name
        ET.SubElement(info, "WERSJA_PROGRAMU").text = self.src_program_ver
        ET.SubElement(info, "DATA_EKSPORTU").text = \
            datetime.date.fromisoformat(self.src_import_time.split("T")[0]).strftime("%d-%m-%Y")
        ET.SubElement(info, "GODZINA_EKSPORTU").text = self.src_import_time.split("T")[1]

        # Contractors

        for idx, entry in self.contractors.items():
            kontr = ET.SubElement(kontrahenci, "KONTRAHENT")
            ET.SubElement(kontr, "ID_KONTRAHENTA").text = entry['int_id']
            ET.SubElement(kontr, "KOD_KONTRAHENTA").text = entry['int_id']
            ET.SubElement(kontr, "NAZWA").text = entry['name'][0:50]
            ET.SubElement(kontr, "NIP").text = entry['nip']
            ET.SubElement(kontr, "PESEL")
            ET.SubElement(kontr, "RODZAJ_EWIDENCJI").text = "1"
            ET.SubElement(kontr, "VAT_CZYNNY").text = "1"
            ET.SubElement(kontr, "KOD_POCZTOWY").text = entry['zip']
            ET.SubElement(kontr, "MIEJSCOWOSC").text = entry['city']
            ET.SubElement(kontr, "ULICA_LOKAL").text = entry['address']
            ET.SubElement(kontr, "NAZWA_PELNA").text = entry['name'][0:200]
            ET.SubElement(kontr, "ADRES").text = '{} {}, {}'.format(entry['zip'], entry['city'], entry['address'])
            ET.SubElement(kontr, "SYMBOL_KRAJU_KONTRAHENTA").text = "PL"
            ET.SubElement(kontr, "NAZWA_KLASYFIKACJI").text = "Ogólna"
            ET.SubElement(kontr, "NAZWA_GRUPY").text = "Ogólna"
            ET.SubElement(kontr, "ODBIORCA").text = "1"
            ET.SubElement(kontr, "DOSTAWCA").text = "1"
            ET.SubElement(kontr, "ID_KLASYFIKACJI").text = "1"
            ET.SubElement(kontr, "ID_GRUPY").text = "1"
            ET.SubElement(kontr, "CZY_KONTRAHENT_UE").text = "0"
            ET.SubElement(kontr, "RAKS_KOD_KONTRAHENTA")
            ET.SubElement(kontr, "ID_KONTRAHENTA_JST").text = "0"

        for idx, entry in self.documents.items():
            if KsaowVars.cfg_purchase_invoice.get() is False and entry['cor'] is False:
                continue
            if KsaowVars.cfg_purchase_invoice_corr.get() is False and entry['cor'] is True:
                continue
            tmp_docs_no += 1
            dokument = ET.SubElement(dokumenty, "DOKUMENT")
            naglowek = ET.SubElement(dokument, "NAGLOWEK_DOKUMENTU")
            vat = ET.SubElement(dokument, "VAT")

            ET.SubElement(naglowek, "RODZAJ_DOKUMENTU").text = "H"
            ET.SubElement(naglowek, "NUMER").text = entry['doc_no']
            if entry['cor'] is True:
                ET.SubElement(naglowek, "NR_DOK_ORYG").text = entry['orig_doc_no']
            else:
                ET.SubElement(naglowek, "NR_DOK_ORYG")

            ET.SubElement(naglowek, "ID_DOKUMENTU_ORYG").text = entry['int_id']
            ET.SubElement(naglowek, "DOK_ZBIOR").text = "0"
            ET.SubElement(naglowek, "ID_KONTRAHENTA").text = self.contractors[entry['id_ctr']]['int_id']
            ET.SubElement(naglowek, "ID_PLATNIKA").text = self.contractors[entry['id_payer']]['int_id']
            ET.SubElement(naglowek, "ID_OPERATORA").text = self.contractors[entry['id_ctr']]['int_id']
            ET.SubElement(naglowek, "ID_KONTRAHENTA_JST").text = "0"
            ET.SubElement(naglowek, "ZAKUP_SPRZEDAZ").text = "z"
            ET.SubElement(naglowek, "ID_MAGAZYNU").text = "1"
            ET.SubElement(naglowek, "SYMBOL_MAGAZYNU").text = "MG"
            ET.SubElement(naglowek, "ID_ROZRACHUNKU").text = "0"
            ET.SubElement(naglowek, "OBLICZANIE_WG_CEN").text = "Netto"
            if entry['cor'] is True:
                ET.SubElement(naglowek, "TYP_DOKUMENTU").text = "FZk"
            else:
                ET.SubElement(naglowek, "TYP_DOKUMENTU").text = "FZ"
            ET.SubElement(naglowek, "OPIS")
            ET.SubElement(naglowek, "SYM_WAL").text = "PLN"
            ET.SubElement(naglowek, "NR_PODSTAWY")
            ET.SubElement(naglowek, "ID_KASY").text = "0"
            ET.SubElement(naglowek, "SYMBOL_KASY")
            ET.SubElement(naglowek, "ID_RACHUNKU").text = "0"
            ET.SubElement(naglowek, "NUMER_RACHUNKU")
            ET.SubElement(naglowek, "TYP_PLATNIKA")
            if entry['cor'] is True:
                ET.SubElement(naglowek, "CZY_DOKUMENT_KOREKTY").text = "1"
            else:
                ET.SubElement(naglowek, "CZY_DOKUMENT_KOREKTY").text = "0"
            ET.SubElement(naglowek, "WYROZNIK").text = entry['full_id']
            ET.SubElement(naglowek, "CZY_FAKTURA_ZALICZKOWA").text = "0"
            ET.SubElement(naglowek, "CZY_FAKTURA_KONCOWA").text = "0"
            ET.SubElement(naglowek, "CZY_KOREKTA_FZAL").text = "0"
            ET.SubElement(naglowek, "CZY_KOREKTA_FZAL_KONCOWEJ").text = "0"
            ET.SubElement(naglowek, "CZY_FZAL_100_PROCENT_BEZ_WZ").text = "0"
            ET.SubElement(naglowek, "CZY_FZAL_100_PROCENT_Z_WZ").text = "0"
            ET.SubElement(naglowek, "POTWIERDZONY_UE").text = "0"
            ET.SubElement(naglowek, "CZY_FISKALNY").text = "0"
            ET.SubElement(naglowek, "FORMA_PLATNOSCI").text = entry['payment_type']
            ET.SubElement(naglowek, "ID_FORMY_PLAT").text = "3"
            ET.SubElement(naglowek, "CZY_POZ_KOSZTOWE_BAZOWE").text = "0"
            ET.SubElement(naglowek, "TROJSTRONNY_UE").text = "0"
            ET.SubElement(naglowek, "WEWNETRZNY").text = "0"
            ET.SubElement(naglowek, "MP").text = "0"
            ET.SubElement(naglowek, "METODA_KASOWA").text = "0"
            ET.SubElement(naglowek, "ODWROTNY").text = "0"
            ET.SubElement(naglowek, "ZALICZKA_ODROCZONA").text = "0"
            ET.SubElement(naglowek, "FAKTURA_DO_PARAGONU").text = "0"
            ET.SubElement(naglowek, "PODLEGA_PP").text = "0"
            pp = ET.SubElement(naglowek, "PODZIELONA_PLATNOSC")
            ET.SubElement(pp, "PP").text = "0"
            ET.SubElement(pp, "PP_NR_FAKTURY")
            ET.SubElement(pp, "PP_NIP")
            ET.SubElement(pp, "PP_KW_VAT_K").text = ".00"
            ET.SubElement(pp, "PP_KW_VAT_R").text = ".00"
            ET.SubElement(naglowek, "RODZAJ_TRANSAKCJI_HANDLOWEJ")
            daty = ET.SubElement(naglowek, "DATY")

            data_wyst_clar = (datetime.date.fromisoformat(entry['date_issue']) - CLCONST).days
            data_otrz_clar = (datetime.date.fromisoformat(entry['date_delivery']) - CLCONST).days
            term_plat_clar = (
                    datetime.date.fromisoformat(entry['date_due']) - CLCONST).days
            ET.SubElement(daty, "DATA_WYSTAWIENIA").text = str(data_wyst_clar)
            ET.SubElement(daty, "DATA_SPRZEDAZY").text = str(data_otrz_clar)
            ET.SubElement(daty, "DATA_WPLYWU").text = str(data_otrz_clar)
            ET.SubElement(daty, "TERMIN_PLATNOSCI").text = str(term_plat_clar)

            wartosci_naglowka = ET.SubElement(naglowek, "WARTOSCI_NAGLOWKA")
            ET.SubElement(wartosci_naglowka, "NETTO_SPRZEDAZY").text = str(entry['sum_netto'])
            ET.SubElement(wartosci_naglowka, "BRUTTO_SPRZEDAZY").text = str(entry['sum_brutto'])
            ET.SubElement(wartosci_naglowka, "NETTO_SPRZEDAZY_WALUTA").text = ".0000"
            ET.SubElement(wartosci_naglowka, "BRUTTO_SPRZEDAZY_WALUTA").text = ".0000"
            ET.SubElement(wartosci_naglowka, "NETTO_ZAKUPU").text = str(entry['sum_netto'])
            ET.SubElement(wartosci_naglowka, "BRUTTO_ZAKUPU").text = str(entry['sum_brutto'])
            ET.SubElement(wartosci_naglowka, "SUMA_NETTO_POZYCJI_FAKTURY_ZALICZKOWEJ").text = ".0000"
            ET.SubElement(wartosci_naglowka, "SUMA_NETTO_POZ_FZAL_WAL").text = ".0000"
            ET.SubElement(wartosci_naglowka, "KW_ROZRACH").text = str(entry['sum_brutto'])
            ET.SubElement(wartosci_naglowka, "KW_ROZRACH_W").text = ".0000"
            ET.SubElement(wartosci_naglowka, "KURS_WALUTY").text = ".00000000"
            ET.SubElement(wartosci_naglowka, "KURS_WALUTY_PZ").text = ".00000000"

            for v_id, v_entry in entry['vat'].items():
                stawka = ET.SubElement(vat, "STAWKA")
                ET.SubElement(stawka, "KOD_VAT").text = str(v_id)
                ET.SubElement(stawka, "NETTO").text = str(v_entry['netto'])
                ET.SubElement(stawka, "VAT").text = str(v_entry['vat'])
                ET.SubElement(stawka, "NETTO_WALUTA").text = ".0000"
                ET.SubElement(stawka, "VAT_WALUTA").text = ".0000"
                ET.SubElement(stawka, "KW_NABYCIA").text = ".00"
                ET.SubElement(stawka, "MARZA").text = "0"
                ET.SubElement(stawka, "DATA_VAT").text = str(data_otrz_clar)
                ET.SubElement(stawka, "DATA_KURSU").text = str(data_otrz_clar)
                ET.SubElement(stawka, "KURS_VAT").text = "1.00000000"
                ET.SubElement(stawka, "ODWROTNY").text = "0"
                ET.SubElement(stawka, "ODWROTNY_TOWAR_USLUGA")

        ET.SubElement(info, "LICZBA_DOKUMENTOW").text = str(tmp_docs_no)

        tree = ET.ElementTree(root)

        # save to file

        try:
            tree.write(filename, encoding="windows-1250", xml_declaration=True)
            messagebox.showinfo('Zapisano!', 'Zapisano dane do pliku {}.'.format(filename))
        except:
            messagebox.showwarning('Błąd!', "Zapisanie pliku {} nie powiodło się!".format(filename))

    def run(self):
        self.mainwindow.mainloop()


if __name__ == '__main__':
    read_cfg()
    app = KsaowApp()
    app.run()
    save_cfg()
