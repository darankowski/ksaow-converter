#!/usr/bin/env python3

import sys
import datetime
import codecs
import json
import webbrowser
import xmltodict
import xml.etree.ElementTree as ET
import tkinter as tk
from tkinter import filedialog

default_path = "C:/Eksport z WFMAG/"

print("""

Prosty konwerter plików z programu KS-AOW (Kamsoft) do WF-Kaper (WAPRO)

W pierwszym oknie wskaż plik do wczytania.
W drugim podaj nazwę pliku docelowego.

""")

root = tk.Tk()
root.withdraw()

file_path = filedialog.askopenfilename(title="Plik do wczytania", filetypes=[("XML", ".xml")], initialdir=default_path)
if not file_path:
    print("Nie wskazano pliku źródłowego, kończę pracę.")
    exit(1)
target_path = filedialog.asksaveasfilename(title="Plik do zapisania", defaultextension="xml", filetypes=[("XML", ".xml")], initialdir=default_path)
if not target_path:
    print("Nie podano nazwy pliku docelowego, kończę pracę.")
    exit(1)

log_path = default_path + "KS-AOW-conv-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + ".txt"
old_stdout = sys.stdout

log_file = open(log_path, "w")

sys.stdout = log_file

print("Wczytuję plik z KS-AOW: %s" % file_path)
print("Zapisuję plik dla WF-Kaper: %s" % target_path)

with codecs.open(file_path, 'r', 'utf-8') as apteka_file:
    apteka = xmltodict.parse(apteka_file.read())

print("Przetwarzam dane - tylko zakupy i korekty zakupu...")

root = ET.Element("MAGIK_EKSPORT")

# Podstawowa struktura

info        = ET.SubElement(root, "INFO_EKSPORTU")
dokumenty   = ET.SubElement(root, "DOKUMENTY")
kontrahenci = ET.SubElement(root, "KARTOTEKA_KONTRAHENTOW")
pracownicy  = ET.SubElement(root, "KARTOTEKA_PRACOWNIKOW")
artykuly    = ET.SubElement(root, "KARTOTEKA_ARTYKULOW")

dostawcy = {}
dostawcy_nazwa = {}
nr_dost = 0
# Naglowek

ET.SubElement(info, "WERSJA_MAGIKA").text = "4.2.0"
ET.SubElement(info, "NAZWA_PROGRAMU").text = apteka['dokumenty']['info']['symbol-systemu']
ET.SubElement(info, "WERSJA_PROGRAMU").text = apteka['dokumenty']['info']['nazwa-systemu']
czas = apteka['dokumenty']['info']['data-czas-generacji']
ET.SubElement(info, "DATA_EKSPORTU").text = datetime.date.fromisoformat(czas.split("T")[0]).strftime("%d-%m-%Y")
ET.SubElement(info, "GODZINA_EKSPORTU").text = czas.split("T")[1]

# Kontrahenci
print()

print("Kontrahenci (tylko dostawcy):")

for apteka_k in apteka['dokumenty']['kartoteki']['kartoteka']:
    if 'DOST' in apteka_k['wewn-ident']:
        nr_dost+=1
        kontr = ET.SubElement(kontrahenci, "KONTRAHENT")
        ET.SubElement(kontr, "ID_KONTRAHENTA").text = apteka_k['wewn-ident'][4:]
        ET.SubElement(kontr, "KOD_KONTRAHENTA").text = apteka_k['wewn-ident'][4:]
        ET.SubElement(kontr, "NAZWA").text = apteka_k['nazwa1'][0:50]
        ET.SubElement(kontr, "NIP").text = apteka_k['nip']
        ET.SubElement(kontr, "PESEL")
        ET.SubElement(kontr, "RODZAJ_EWIDENCJI").text = "1"
        ET.SubElement(kontr, "VAT_CZYNNY").text = "1"
        if 'kod-pocztowy' in apteka_k['adres-telefon']:
            ET.SubElement(kontr, "KOD_POCZTOWY").text = apteka_k['adres-telefon']['kod-pocztowy']
        else:
            ET.SubElement(kontr, "KOD_POCZTOWY")
        ET.SubElement(kontr, "MIEJSCOWOSC").text = apteka_k['adres-telefon']['miejscowosc']
        ET.SubElement(kontr, "ULICA_LOKAL").text = apteka_k['adres-telefon']['adres']
        ET.SubElement(kontr, "NAZWA_PELNA").text = apteka_k['nazwa1'][0:200]
        if 'kod-pocztowy' in apteka_k['adres-telefon']:
            ET.SubElement(kontr, "ADRES").text = "%s %s, %s" % (apteka_k['adres-telefon']['kod-pocztowy'], apteka_k['adres-telefon']['miejscowosc'], apteka_k['adres-telefon']['adres'])
        else:
            ET.SubElement(kontr, "ADRES").text = " %s, %s" % (apteka_k['adres-telefon']['miejscowosc'], apteka_k['adres-telefon']['adres'])
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

        dostawcy[apteka_k['@lp']] = apteka_k['wewn-ident'][4:]
        dostawcy_nazwa[apteka_k['@lp']] = apteka_k['nazwa1']

        print("%3d: ID: %-6s NIP: %-15s %-40s" % (nr_dost, apteka_k['wewn-ident'][4:], apteka_k['nip'], apteka_k['nazwa1']))

#        print("%d, %d, %s, %s" % (int(apteka_k['@lp']), int(apteka_k['wewn-ident'][4:]), apteka_k['nazwa1'], apteka_k['nip']))

print()
print("Skonczylem - teraz dokumenty:")
print()
# Dokumenty

print("Lp. | Dokument                  | Data wyst. | Data wpł.  | Korekta | Dostawca                                 | Wartość netto | Wartość brutto")
print("----+---------------------------+------------+------------+---------+------------------------------------------+---------------+---------------")
how_many = 0

for apteka_k in apteka['dokumenty']['dokument']:
#    print(apteka_k['@lp'])
    if apteka_k['naglowek']['rodzaj-dokumentu'] == 'Z':   # chcemy tylko faktury zakupu
        how_many+=1
        dokument = ET.SubElement(dokumenty, "DOKUMENT")
        naglowek = ET.SubElement(dokument, "NAGLOWEK_DOKUMENTU")
        vat = ET.SubElement(dokument, "VAT")

#        print(apteka_k['naglowek'])

        # wypelnij naglowek
        ET.SubElement(naglowek, "RODZAJ_DOKUMENTU").text = "H"
        ET.SubElement(naglowek, "NUMER").text = apteka_k['naglowek']['nr-dokumentu']
        if apteka_k['naglowek']['czy-korekta'] == "false":
            ET.SubElement(naglowek, "NR_DOK_ORYG")
        else:
            ET.SubElement(naglowek, "NR_DOK_ORYG").text = apteka_k['naglowek-kor']['nr-dokumentu-kor']

        ET.SubElement(naglowek, "ID_DOKUMENTU_ORYG").text = apteka_k['naglowek']['wewn-ident'][4:]
        ET.SubElement(naglowek, "DOK_ZBIOR").text = "0"
        ET.SubElement(naglowek, "ID_KONTRAHENTA").text = dostawcy[apteka_k['naglowek']['kontrahent']]
        ET.SubElement(naglowek, "ID_PLATNIKA").text = dostawcy[apteka_k['naglowek']['sprzedawca']]
        ET.SubElement(naglowek, "ID_OPERATORA").text = dostawcy[apteka_k['naglowek']['kontrahent']]
        ET.SubElement(naglowek, "ID_KONTRAHENTA_JST").text = "0"
        ET.SubElement(naglowek, "ZAKUP_SPRZEDAZ").text = "z"
        ET.SubElement(naglowek, "ID_MAGAZYNU").text = "1"
        ET.SubElement(naglowek, "SYMBOL_MAGAZYNU").text = "MG"
        ET.SubElement(naglowek, "ID_ROZRACHUNKU").text = "0"
        ET.SubElement(naglowek, "OBLICZANIE_WG_CEN").text = "Netto"
        if apteka_k['naglowek']['czy-korekta'] == "false":
            ET.SubElement(naglowek, "TYP_DOKUMENTU").text = "FZ"
        else:
            ET.SubElement(naglowek, "TYP_DOKUMENTU").text = "FZk"
        
        ET.SubElement(naglowek, "OPIS")
        ET.SubElement(naglowek, "SYM_WAL").text = "PLN"
        ET.SubElement(naglowek, "NR_PODSTAWY")
        ET.SubElement(naglowek, "ID_KASY").text = "0"
        ET.SubElement(naglowek, "SYMBOL_KASY")
        ET.SubElement(naglowek, "ID_RACHUNKU").text = "0"
        ET.SubElement(naglowek, "NUMER_RACHUNKU")
        ET.SubElement(naglowek, "TYP_PLATNIKA")
        if apteka_k['naglowek']['czy-korekta'] == "false":
            ET.SubElement(naglowek, "CZY_DOKUMENT_KOREKTY").text = "0"
        else:
            ET.SubElement(naglowek, "CZY_DOKUMENT_KOREKTY").text = "1"
        
        ET.SubElement(naglowek, "WYROZNIK").text = apteka_k['naglowek']['wewn-ident']
        ET.SubElement(naglowek, "CZY_FAKTURA_ZALICZKOWA").text = "0"
        ET.SubElement(naglowek, "CZY_FAKTURA_KONCOWA").text = "0"
        ET.SubElement(naglowek, "CZY_KOREKTA_FZAL").text = "0"
        ET.SubElement(naglowek, "CZY_KOREKTA_FZAL_KONCOWEJ").text = "0"
        ET.SubElement(naglowek, "CZY_FZAL_100_PROCENT_BEZ_WZ").text = "0"
        ET.SubElement(naglowek, "CZY_FZAL_100_PROCENT_Z_WZ").text = "0"
        ET.SubElement(naglowek, "POTWIERDZONY_UE").text = "0"
        ET.SubElement(naglowek, "CZY_FISKALNY").text = "0"
        ET.SubElement(naglowek, "NR_DOKM").text = apteka_k['naglowek']['nr-dokumentu']
        ET.SubElement(naglowek, "FORMA_PLATNOSCI").text = apteka_k['naglowek']['forma-platnosci']['symbol']
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
        wartosci_naglowka = ET.SubElement(naglowek, "WARTOSCI_NAGLOWKA")

        # przygotujemy juz teraz, wypelnimy pozniej

        netto_sprzedaz = ET.SubElement(wartosci_naglowka, "NETTO_SPRZEDAZY")
        brutto_sprzedaz = ET.SubElement(wartosci_naglowka, "BRUTTO_SPRZEDAZY")
        ET.SubElement(wartosci_naglowka, "NETTO_SPRZEDAZY_WALUTA").text = ".0000"
        ET.SubElement(wartosci_naglowka, "BRUTTO_SPRZEDAZY_WALUTA").text = ".0000"
        netto_zakup = ET.SubElement(wartosci_naglowka, "NETTO_ZAKUPU")
        brutto_zakup = ET.SubElement(wartosci_naglowka, "BRUTTO_ZAKUPU")
        ET.SubElement(wartosci_naglowka, "SUMA_NETTO_POZYCJI_FAKTURY_ZALICZKOWEJ").text = ".0000"
        ET.SubElement(wartosci_naglowka, "SUMA_NETTO_POZ_FZAL_WAL").text = ".0000"
        kw_rozrach = ET.SubElement(wartosci_naglowka, "KW_ROZRACH")
        ET.SubElement(wartosci_naglowka, "KW_ROZRACH_W").text = ".0000"
        ET.SubElement(wartosci_naglowka, "KURS_WALUTY").text = ".00000000"
        ET.SubElement(wartosci_naglowka, "KURS_WALUTY_PZ").text = ".00000000"

        # wypelnij daty
        ET.SubElement(daty, "DATA_WYSTAWIENIA").text = str((datetime.date.fromisoformat(apteka_k['naglowek']['data-wystawienia']) - datetime.date(1800,12,28)).days)
#        ET.SubElement(daty, "DATA_WYSTAWIENIA").text = str((datetime.date.fromisoformat(apteka_k['naglowek']['data-otrzymania']) - datetime.date(1800,12,28)).days)
#        ET.SubElement(daty, "DATA_SPRZEDAZY").text = str((datetime.date.fromisoformat(apteka_k['naglowek']['data-wystawienia']) - datetime.date(1800,12,28)).days)
        ET.SubElement(daty, "DATA_SPRZEDAZY").text = str((datetime.date.fromisoformat(apteka_k['naglowek']['data-otrzymania']) - datetime.date(1800,12,28)).days)
        ET.SubElement(daty, "DATA_WPLYWU").text = str((datetime.date.fromisoformat(apteka_k['naglowek']['data-otrzymania']) - datetime.date(1800,12,28)).days)
        ET.SubElement(daty, "TERMIN_PLATNOSCI").text = str((datetime.date.fromisoformat(apteka_k['naglowek']['termin-platnosci']['data']) - datetime.date(1800,12,28)).days)


        # kwoty VAT
        apt_v_netto = {}
        apt_v_vat = {}
        for apt_vat in apteka_k['podsumowanie-fk']['kwoty']['kwota']:
            if 'stawka-vat' in apt_vat:
                if 'kwd-netto-zakupu' in apt_vat['symbol']:
                    apt_v_netto[apt_vat['stawka-vat']] = apt_vat['wartosc']
                if 'kwd-vat-zakupu' in apt_vat['symbol']:
                    apt_v_vat[apt_vat['stawka-vat']] = apt_vat['wartosc']
            else:
                if 'kwd-netto-zakupu' in apt_vat['symbol']:
                    netto_zakup.text = str("%.4f" % float(apt_vat['wartosc']))
                    netto_sprzedaz.text = str("%.4f" % float(apt_vat['wartosc']))
                if 'kwd-brutto-zakupu' in apt_vat['symbol']:
                    brutto_zakup.text = str("%.4f" % float(apt_vat['wartosc']))
                    brutto_sprzedaz.text = str("%.4f" % float(apt_vat['wartosc']))
                    kw_rozrach.text = str("%.4f" % float(apt_vat['wartosc']))

        for st_vat in apt_v_netto:
            stawka = ET.SubElement(vat, "STAWKA")
            ET.SubElement(stawka, "KOD_VAT").text = str(st_vat)
            ET.SubElement(stawka, "NETTO").text = str("%.4f" % float(apt_v_netto[st_vat]))
            ET.SubElement(stawka, "VAT").text = str("%.4f" % float(apt_v_vat[st_vat]))
            ET.SubElement(stawka, "NETTO_WALUTA").text = ".0000"
            ET.SubElement(stawka, "VAT_WALUTA").text = ".0000"
            ET.SubElement(stawka, "KW_NABYCIA").text = ".00"
            ET.SubElement(stawka, "MARZA").text = "0"
            ET.SubElement(stawka, "DATA_VAT").text = str((datetime.date.fromisoformat(apteka_k['naglowek']['data-otrzymania']) - datetime.date(1800,12,28)).days)
            ET.SubElement(stawka, "DATA_KURSU").text = str((datetime.date.fromisoformat(apteka_k['naglowek']['data-otrzymania']) - datetime.date(1800,12,28)).days)
            ET.SubElement(stawka, "KURS_VAT").text = "1.00000000"
            ET.SubElement(stawka, "ODWROTNY").text = "0"
            ET.SubElement(stawka, "ODWROTNY_TOWAR_USLUGA")

        print("%3d | %-25s | %-10s | %-10s | %-7s | %-40s | %13.2f | %13.2f" % (how_many, apteka_k['naglowek']['nr-dokumentu'], apteka_k['naglowek']['data-wystawienia'], apteka_k['naglowek']['data-otrzymania'],
                                                                            "TAK" if apteka_k['naglowek']['czy-korekta'] == "true" else "", dostawcy_nazwa[apteka_k['naglowek']['kontrahent']], float(netto_zakup.text), float(brutto_zakup.text)))


#            print(apteka_k['podsumowanie-fk'])

print()
print("Skończyłem. Liczba znalezionych dokumentów: %d" % how_many)

# Zaktualizuj liczbe dokumentow

ET.SubElement(info, "LICZBA_DOKUMENTOW").text = str(how_many)

tree = ET.ElementTree(root)

print()
print("Zapisuję...")

tree.write(target_path, encoding="windows-1250", xml_declaration=True)

print("KONIEC")

sys.stdout = old_stdout
log_file.close()

webbrowser.open(log_path)