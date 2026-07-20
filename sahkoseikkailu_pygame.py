"""Sähköseikkailun 30 tehtävän Pygame-käyttöliittymä.

Tehtävien arvonta, laskenta ja kytkentäkaaviot tulevat olemassa olevasta
elektroniikka.py-tiedostosta. Pygame hoitaa koko näkyvän käyttöliittymän ja
kaikki napsautukset.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import re
import sys
import tempfile
import types
from pathlib import Path
from typing import Iterable

if "--self-test" in os.sys.argv:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

# Tehtävämoottori on samassa tiedostossa kuin vanha Tkinter-käyttöliittymä.
# Pygame-ympäristö ei tarvitse Tkinteriä, joten tarjoamme tuontia varten vain
# kevyet nimipaikat, jos tämän Pythonin mukana ei tullut _tkinter-moduulia.
try:
    import elektroniikka as legacy
except ModuleNotFoundError as error:
    if error.name != "_tkinter":
        raise
    tkinter_stub = types.ModuleType("tkinter")
    tkinter_stub.TclError = RuntimeError
    messagebox_stub = types.ModuleType("tkinter.messagebox")
    tkinter_stub.messagebox = messagebox_stub
    sys.modules["tkinter"] = tkinter_stub
    sys.modules["tkinter.messagebox"] = messagebox_stub
    import elektroniikka as legacy


WIDTH, HEIGHT = 1240, 760
FPS = 60
BG = "#071628"
PANEL = "#112844"
PANEL_BORDER = "#245177"
CYAN = "#52dcf4"
YELLOW = "#ffd255"
WHITE = "#f5f7fb"
MUTED = "#9db0c8"
GREEN = "#55e690"
RED = "#ff6078"
BUTTON = "#e8edf5"
BUTTON_HOVER = "#d5e7fa"
BUTTON_DOWN = "#b9d7f4"
INK = "#0a1727"

HINTS = {
    1: "Ohmin laki yhdistää jännitteen, virran ja resistanssin: U = RI.",
    2: "Sarjaan kytkettyjen samansuuntaisten lähteiden jännitteet summataan.",
    3: "Tässä vaihtovirtapiirissä on vain vastus. Siksi impedanssi on yhtä suuri kuin resistanssi: Z = R.",
    4: "Laske ensin rinnakkain kytkettyjen vastusten kokonaisresistanssi: 1/Rkok = 1/R1 + 1/R2.",
    5: "Rinnakkain kytkettyjen vastusten yli on sama jännite. Laske jokaisen vastuksen virta kaavalla I = U/R ja summaa virrat.",
    6: "Kaksi samanlaista rinnakkain kytkettyä jännitelähdettä tuottaa saman jännitteen kuin yksi lähde.",
    7: "Kondensaattorin reaktanssi on XC = 1/(2πfC). Kun piirissä on vain kondensaattori, impedanssin itseisarvo on |Z| = XC.",
    8: "Käämin reaktanssi on XL = 2πfL. Kun piirissä on vain käämi, impedanssin itseisarvo on |Z| = XL.",
    9: "Laske ensin käämin reaktanssi XL = 2πfL. Vastuksen ja käämin sarjapiirissä impedanssin itseisarvo on |Z| = √(R² + XL²).",
    10: "Laske ensin käämin reaktanssi XL = 2πfL. Vastuksen ja käämin sarjapiirin impedanssin itseisarvo on |Z| = √(R² + XL²).",
    11: "Laske ensin kondensaattorin reaktanssi XC = 1/(2πfC). Vastuksen ja kondensaattorin sarjapiirissä |Z| = √(R² + XC²).",
    12: "Käämin ja kondensaattorin vaikutukset vähentävät toisiaan, joten sarjapiirin impedanssin itseisarvo on |XL − XC|.",
    13: "Käämi ja kondensaattori siirtävät virran vaihetta vastakkaisiin suuntiin, joten kokonaisreaktanssi on X = XL − XC.",
    14: "Rinnakkaispiirissä on usein helpointa summata haarojen kompleksiset admittanssit.",
    15: "Laske R- ja L-haarojen admittanssit erikseen ja summaa ne kokonaisadmittanssiksi Y. Piirin kokonaisimpedanssi on kokonaisadmittanssin käänteisluku: Z = 1/Y.",
    16: "Rinnakkain kytkettyjen kondensaattorien kapasitanssit summataan. Kondensaattorin reaktanssi pienenee taajuuden kasvaessa.",
    17: "LC-rinnakkaispiirin kokonaisadmittanssi saadaan laskemalla käämin ja kondensaattorin admittanssit yhteen.",
    18: "RLC-rinnakkaispiirissä kokonaisadmittanssi on YR + YL + YC.",
    19: "Sovella solmuun Kirchhoffin virtalakia ja kumpaankin silmukkaan Kirchhoffin jännitelakia.",
    20: "Kirjoita solmuille V1 ja V2 Kirchhoffin virtalain mukaiset yhtälöt.",
    21: "Merkitse ylä- ja alasolmun jännite-ero V:ksi. Kirjoita kunkin vastuksen virta V:n avulla ja käytä ΣI = 0.",
    22: "Avoimessa lähtöportissa lähtöhaaran virta on nolla. Etsi portin solmujännite.",
    23: "Riippumaton ideaalinen jännitelähde deaktivoidaan korvaamalla se oikosululla.",
    24: "Kun kaksi vastusta on samojen solmujen välissä, niiden käänteiset resistanssit summataan.",
    25: "Tarkista, mikä vastus on portin kanssa sarjassa ja mitkä sisävastukset ovat rinnan.",
    26: "Oikosuljetun portin päiden välinen jännite on nolla. Selvitä ensin sitä syöttävän solmun jännite.",
    27: "Käämin näkemä C1:n ja C2:n kapasitanssi on niiden sarjakapasitanssi. Käytä LC-resonanssiehtoa.",
    28: "Merkitse R1:n, R3:n ja R5:n yhteisen liitospisteen sekä R2:n, R4:n ja R5:n yhteisen liitospisteen jännitteet tuntemattomiksi. Muodosta kummallekin liitospisteelle Kirchhoffin virtalain mukainen yhtälö.",
    29: "Muodosta kummankin LC-haaran kompleksinen admittanssi ja käsittele Cg niiden välisenä impedanssina.",
    30: "Aloita laskemalla R2:n ja L2:n rinnankytkennän impedanssi. Tämä yhdistelmä on sarjassa C2:n kanssa, ja niiden yhteisimpedanssi on rinnan C1:n kanssa. Lisää lopuksi piirin sarjassa olevien muiden komponenttien impedanssit.",
}

RULES_TEXT = """PELIN TAVOITE
Ratkaise kaikki 30 tehtävää ja läpäise niiden jälkeen avautuva loppukoe.

PISTEET
- Tehtävistä 1–26 saa ensimmäisestä oikeasta suorituksesta 10 pistettä.
- Jokeritehtävistä 27–30 saa ensimmäisestä oikeasta suorituksesta 20 pistettä.
- Väärä vastaus ei vähennä pelipisteitä.
- Kolmen väärän vastauksen jälkeen tehtävään arvotaan uudet lähtöarvot.
- Samasta tehtävästä saa pisteet vain kerran.

LISÄKYSYMYS, VIHJE JA VASTAUS
- Ennen varsinaisen tehtävän ratkaisua lisäkysymyksen oikeasta vastauksesta saa 5 pistettä. Tämä vähennetään varsinaisen tehtävän jäljellä olevasta palkkiosta, joten tavallisen tehtävän kokonaispalkkio on enintään 10 pistettä ja jokeritehtävän 20 pistettä.
- Varsinaisen tehtävän ratkaisemisen jälkeen lisäkysymyksen voi edelleen tehdä, mutta siitä ei enää saa pisteitä.
- Vihje maksaa 5 pistettä.
- Valmiin numeroarvon näyttäminen maksaa 10 pistettä. Kun oikea vastaus suljetaan, tehtävään arvotaan uudet lähtöarvot.
- Vihjettä tai valmista vastausta ei voi avata, jos pisteet eivät riitä.
- Peli varaa lisäksi riittävästi pisteitä seuraavan tehtäväryhmän avaamiseen. Jos apua ei voi vielä ostaa, peli kertoo pistemäärän, joka tarvitaan vihjeen tai oikean vastauksen avaamiseen ilman etenemisen lukkiutumista.

ETENEMINEN
- Tehtävät 1–5 ovat avoinna heti.
- Tehtävät 6–10 avautuvat 40 pisteellä.
- Tehtävät 11–15 avautuvat 90 pisteellä.
- Tehtävät 16–20 avautuvat 130 pisteellä.
- Tehtävät 21–26 avautuvat 170 pisteellä.
- Jokeritehtävät 27–30 avautuvat 220 pisteellä.
- Kun uusi tehtäväryhmä avautuu, peli näyttää siitä ilmoituksen.
- Kerran avattu tehtäväryhmä pysyy avoinna, vaikka pisteitä käytettäisiin myöhemmin.

LOPPUKOE
- Kun kaikki 30 tehtävää on ratkaistu, LOPPUKOE-painike aktivoituu ja peli ilmoittaa kokeen olevan valmis. Koe käynnistyy vasta painikkeesta. Esittelytilassa painike on käytettävissä heti.
- Jokaisessa kysymyksessä on neljä vaihtoehtoa. Oikeita vaihtoehtoja voi olla yksi tai useita.
- Yhden oikean vaihtoehdon kysymyksessä täsmälleen oikea valinta antaa +1 pisteen, tyhjä vastaus 0 pistettä ja väärä vastaus −0,5 pistettä.
- Usean oikean vaihtoehdon kysymyksessä jokainen oikein käsitelty vaihtoehto antaa +0,25 pistettä ja jokainen väärin käsitelty vaihtoehto −0,25 pistettä. Oikein käsitelty tarkoittaa, että oikea vaihtoehto valitaan tai väärä vaihtoehto jätetään valitsematta.
- Loppukokeen kokonaispistemäärä ei voi olla alle nollan.
- Peli läpäistään vähintään tuloksella 8/10.

EDISTYMINEN näyttää ratkaistut tehtävät. TALLENNA säilyttää tilanteen ja avatut tehtävät. ALOITA ALUSTA nollaa pisteet ja suoritukset."""

ADVICE_TEXT = """- Ratkaise helpot tehtävät mahdollisuuksien mukaan ilman apua. Näin säästät pisteitä vaikeampiin tehtäviin.

- Väärästä vastauksesta ei menetä pisteitä. Tarkista siis laskusi rauhassa ja uskalla yrittää ennen vihjeen avaamista. Kolmas väärä vastaus vaihtaa lähtöarvot, joten oikeaa vastausta ei kannata yrittää arvata.

- Jos olet tehtävien kanssa jumissa tai pisteet ovat vähissä, aloita tehtäväkohtaisesta lisäkysymyksestä. Se kertaa tarvittavaa käsitettä ja antaa oikeasta vastauksesta 5 pistettä.

- Käytä ensin vihjettä. Se ohjaa oikeaan lakiin tai laskutapaan, mutta jättää varsinaisen ratkaisun sinulle.

- Avaa valmis vastaus vasta viimeisenä keinona. Se maksaa enemmän pisteitä ja pakottaa ratkaisemaan tehtävän uusilla lähtöarvoilla.

- Jos vaikea tehtävä ei aukea, palaa aiempiin saman aiheen tehtäviin. Tavoitteena ei ole kerätä mahdollisimman suurta pistemäärää, vaan oppia ratkaisemaan kaikki tehtävätyypit.

- Anna numeeriset vastaukset yhden desimaalin tarkkuudella.

- Usean vastauksen tehtävissä erota arvot puolipisteillä.

- Tekoälyn käyttö ei ole suositeltavaa. Se on oikotie tehtävän ratkaisuun, mutta ei asioiden oppimiseen."""

NOTATION_TEXT = """R — resistanssi, yksikkö ohmi (Ω)

L — induktanssi, yksikkö henry (H)

C — kapasitanssi, yksikkö faradi (F)

Z — impedanssi eli vaihtovirran kulkua vastustava suure, yksikkö ohmi (Ω)

Y — admittanssi eli impedanssin käänteisluku, yksikkö siemens (S)

G — konduktanssi eli admittanssin reaaliosa. Puhtaalle vastukselle G = 1/R, yksikkö siemens (S)

B — suskeptanssi eli admittanssin imaginääriosa, joka kuvaa käämien ja kondensaattorien vaikutusta vaihtovirran kulkuun, yksikkö siemens (S)

U — jännite eli kahden pisteen välinen potentiaaliero, yksikkö voltti (V)

Ueff — jännitteen tehollisarvo. Sinimuotoiselle jännitteelle Ueff = Umax/√2, yksikkö voltti (V)

Umax — sinimuotoisen jännitteen huippuarvo eli hetkellisen jännitteen suurin itseisarvo, yksikkö voltti (V)

Ieff — virran tehollisarvo. Sinimuotoiselle virralle Ieff = Imax/√2, yksikkö ampeeri (A)

Imax — sinimuotoisen virran huippuarvo eli hetkellisen virran suurin itseisarvo, yksikkö ampeeri (A)

RTh — Thévenin-vastus eli portista nähtävä piirin sisäinen vastus, yksikkö ohmi (Ω)

UTh — Thévenin-jännite eli avoimen lähtöportin jännite, yksikkö voltti (V)

Isc — oikosulkuvirta eli oikosuljetun portin läpi kulkeva virta, yksikkö ampeeri (A)

Rkok — piirin tai vastusryhmän kokonaisresistanssi, yksikkö ohmi (Ω)

XC — kapasitiivinen reaktanssi, yksikkö ohmi (Ω)

XL — induktiivinen reaktanssi, yksikkö ohmi (Ω)

f — taajuus, yksikkö hertsi (Hz)"""

FINAL_EXAM_QUESTIONS = (
    ("Mikä kaava kuvaa Ohmin lakia?",
     ("U = RI", "P = UI", "Q = CU", "XL = 2πfL"), {0}),
    ("Mitkä väitteet pätevät vastusten rinnankytkennässä?",
     ("Kaikkien haarojen yli on sama jännite", "Kokonaisvirta on haaravirtojen summa",
      "Kokonaisresistanssi on aina suurin vastus", "Haarojen virrat ovat aina yhtä suuret"), {0, 1}),
    ("Miten ideaalisen käämin reaktanssi muuttuu taajuuden kasvaessa?",
     ("Se kasvaa", "Se pienenee", "Se pysyy aina nollana", "Se muuttuu kapasitanssiksi"), {0}),
    ("Mitkä väitteet pätevät ideaaliseen kondensaattoriin vaihtovirralla?",
     ("XC = 1/(2πfC)", "Reaktanssi pienenee taajuuden kasvaessa",
      "Virta johtaa jännitettä", "Reaktanssi kasvaa kapasitanssin kasvaessa"), {0, 1, 2}),
    ("Mitä Kirchhoffin virtalaki sanoo solmusta?",
     ("Tulevien virtojen summa on lähtevien virtojen summa", "Jännitteiden summa on aina yksi voltti",
      "Kaikkien haarojen resistanssit ovat samat", "Solmussa ei voi olla yli kahta haaraa"), {0}),
    ("Mitkä toimet kuuluvat Thévenin-vastuksen määrittämiseen?",
     ("Riippumaton ideaalinen jännitelähde oikosuljetaan",
      "Riippumaton ideaalinen virtalähde avataan",
      "Portista katsotaan piirin sisään", "Kaikki vastukset poistetaan"), {0, 1, 2}),
    ("Milloin ideaalinen RLC-sarjapiiri on resonanssissa?",
     ("Kun XL = XC", "Kun R = 0 aina", "Kun taajuus on aina 50 Hz", "Kun U = I"), {0}),
    ("Mitkä väitteet admittanssista ovat oikein?",
     ("Y = 1/Z", "Rinnakkaisten haarojen admittanssit voidaan summata",
      "Sen yksikkö on siemens", "Se on aina pelkkä reaaliluku"), {0, 1, 2}),
    ("Mitkä suureet voivat olla kompleksisia vaihtovirtapiirin laskuissa?",
     ("Impedanssi", "Admittanssi", "Reaktanssia sisältävä kokonaisvastus", "Taajuus hertseinä"), {0, 1, 2}),
    ("Mitä tapahtuu ideaalisen LC-rinnakkaispiirin resonanssissa?",
     ("Käämin ja kondensaattorin suskeptanssit kumoavat toisensa",
      "Kokonaisadmittanssi lähestyy nollaa", "Impedanssi kasvaa hyvin suureksi",
      "Lähdevirta kasvaa äärettömäksi"), {0, 1, 2}),
)

CONCEPT_SECTIONS = {
    "electrical": ("JÄNNITE- JA VIRTASUUREET", """Lähdejännite on jännitelähteen tuottama jännite. Napajännite on jännitelähteen napojen välinen potentiaaliero. Ideaalisella jännitelähteellä nämä ovat samat. Todellisen lähteen napajännite voi kuormitettuna olla lähdejännitettä pienempi lähteen sisäisen resistanssin vuoksi.

Kokonaisvirta tarkoittaa koko piirin virtaa ennen sen jakautumista rinnakkaisiin osiin tai niiden yhdistymisen jälkeen. Se on rinnakkaisten osien virtojen summa. Pelkkä kokonaisarvo ei ole sähköopin itsenäinen suure: on kerrottava, tarkoitetaanko esimerkiksi kokonaisvirtaa, kokonaisresistanssia vai kokonaisimpedanssia.

Vaihtovirran tehollisarvo on sellaisen tasavirran arvo, joka tuottaa vastuksessa saman keskimääräisen tehon. Sinimuotoiselle jännitteelle Ueff = Umax/√2 ja virralle Ieff = Imax/√2. Tehtävissä ilmoitettu vaihtojännite on tehollisarvo, ellei toisin mainita. Hetkellisarvo puolestaan muuttuu ajan mukana, ja huippuarvo on hetkellisarvon suurin itseisarvo."""),
    "node": ("SOLMU JA KIRCHHOFFIN VIRTALAKI", """Solmu on virtapiirin kohta, jossa vähintään kolme haaraa yhdistyy.

Kirchhoffin virtalain mukaan solmuun tulevien virtojen summa on yhtä suuri kuin solmusta lähtevien virtojen summa."""),
    "thevenin": ("THÉVENIN-JÄNNITE JA THÉVENIN-VASTUS", """Thévenin-jännite UTh on avoimen lähtöportin A–B välinen jännite. Avoimeen porttiin ei ole kytketty kuormaa, joten sen läpi ei kulje virtaa.

Thévenin-vastus RTh on vastus, joka nähdään katsottaessa piiriä portista A–B. Sitä määritettäessä riippumaton ideaalinen jännitelähde korvataan oikosululla ja riippumaton ideaalinen virtalähde avoimella piirillä. Thévenin-vastus voidaan määrittää myös suhteesta RTh = UTh/Isc, missä Isc on portin oikosulkuvirta."""),
    "admittance": ("ADMITTANSSI, KONDUKTANSSI JA SUSKEPTANSSI", """Admittanssi Y kertoo, kuinka helposti vaihtovirta kulkee piirin läpi. Se on impedanssin Z käänteisluku:

Y = 1/Z

Admittanssin yksikkö on siemens (S). Vaihtovirtapiirissä admittanssi esitetään kompleksilukuna, koska virta ja jännite voivat olla eri vaiheessa. Tällöin Y = G + jB, missä G on konduktanssi ja B suskeptanssi.

Konduktanssi G on admittanssin reaaliosa. Se kuvaa resistiivisen osan kykyä johtaa virtaa. Puhtaalle vastukselle G = 1/R.

Suskeptanssi B on admittanssin imaginääriosa. Se kuvaa kondensaattorien ja käämien vaikutusta vaihtovirran kulkuun. Merkintätavalla Y = G + jB kondensaattorin suskeptanssi on positiivinen ja käämin negatiivinen. Myös konduktanssin ja suskeptanssin yksikkö on siemens (S).

Admittanssi on erityisen hyödyllinen rinnakkaispiirissä: rinnakkaisten haarojen admittanssit voidaan summata suoraan."""),
    "opamp": ("OPERAATIOVAHVISTIN", """Operaatiovahvistimessa on kaksi tuloa: ei-invertoiva tulo (+) ja invertoiva tulo (−). Lähtöjännite määräytyy näiden tulojen jännitteiden erotuksen perusteella.

Ideaalisen operaatiovahvistimen tuloihin ei kulje virtaa. Takaisinkytketyssä piirissä operaatiovahvistin voi syöttää piiriin energiaa ja ylläpitää värähtelyä, jonka taajuuden määrää varsinainen LC-verkko."""),
    "resonance": ("RESONANSSITAAJUUS JA TAKAISINKYTKENTÄ", """Resonanssitaajuus on taajuus, jolla käämin ja kondensaattorien muodostama LC-verkko värähtelee luontaisesti. Tällä taajuudella energia siirtyy vuorotellen käämin magneettikentän ja kondensaattorien sähkökentän välillä. Tässä piirissä käämin näkemä kapasitanssi on C1:n ja C2:n sarjakapasitanssi C = C1C2/(C1 + C2), ja resonanssitaajuus on f0 = 1/(2π√(LC)).

Takaisinkytkentä tarkoittaa sitä, että osa operaatiovahvistimen lähtösignaalista johdetaan takaisin sen tuloon. Tässä oskillaattorissa takaisinkytkentä vahvistaa LC-verkon värähtelyä ja auttaa ylläpitämään sitä.

Takaisinkytkentävastus R1 on vastus, jonka kautta lähtösignaalia johdetaan takaisin tuloon. Se vaikuttaa takaisinkytkennän voimakkuuteen ja värähtelyn käynnistymiseen, mutta tämän ideaalisen tehtävämallin resonanssitaajuuden määräävät L, C1 ja C2."""),
    "parallel_resonance": ("LC-RINNAKKAISPIIRIN RESONANSSI", """Resonanssi tarkoittaa tässä tilannetta, jossa käämin ja kondensaattorin vaikutukset kumoavat toisensa lähteen näkökulmasta. Käämin ja kondensaattorin haaravirrat ovat yhtä suuret mutta vastakkaisvaiheiset, joten ideaalisen piirin lähteestä ottama kokonaisvirta on nolla.

Suskeptanssi B on admittanssin imaginääriosa. Käämin suskeptanssia kutsutaan induktiiviseksi suskeptanssiksi ja kondensaattorin suskeptanssia kapasitiiviseksi suskeptanssiksi. Kun admittanssi kirjoitetaan muodossa Y = G + jB, käämin suskeptanssi on BL = −1/(ωL) ja kondensaattorin suskeptanssi BC = ωC.

Rinnakkaisresonanssissa BL + BC = 0: suskeptanssit ovat yhtä suuret itseisarvoltaan mutta vastakkaismerkkiset. Siksi ne kumoavat toisensa. Ideaalisen LC-rinnakkaispiirin kokonaisadmittanssi on tällöin nolla ja impedanssi äärettömän suuri."""),
}

BONUS_QUESTION_OVERRIDES = {
    26: ("Miten RLC-rinnakkaispiirin kokonaisadmittanssi muodostetaan?",
         ("Haarojen admittanssit summataan kompleksilukuina",
          "Haarojen impedanssit summataan suoraan",
          "Valitaan pienin reaktanssi"), 0),
    29: ("Mitä tapahtuu käämin ja kondensaattorin suskeptansseille ideaalisen LC-rinnakkaispiirin resonanssissa?",
         ("Ne kumoavat toisensa", "Ne kaksinkertaistuvat",
          "Molemmat muuttuvat resistanssiksi"), 0),
    30: ("Mikä on turvallisin tapa pelkistää yhdistetty sarja- ja rinnakkaispiiri?",
         ("Aloittaa sisimmästä selvästä osapiiristä ja edetä ulospäin",
          "Summata kaikki komponenttiarvot",
          "Jättää reaktiiviset komponentit huomiotta"), 0),
}


def font(size: int, bold: bool = False) -> pygame.font.Font:
    return pygame.font.SysFont("Arial", max(9, int(size)), bold=bold)


def draw_text(surface, text, position, size, color=WHITE, bold=False,
              anchor="topleft"):
    image = font(size, bold).render(str(text), True, color)
    rect = image.get_rect()
    setattr(rect, anchor, position)
    surface.blit(image, rect)
    return rect


def wrapped_lines(text: str, face: pygame.font.Font, width: int) -> list[str]:
    lines = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        line = words.pop(0)
        for word in words:
            candidate = f"{line} {word}"
            if face.size(candidate)[0] <= width:
                line = candidate
            else:
                lines.append(line)
                line = word
        lines.append(line)
    return lines


def draw_fitted_text(surface, text, rect, start_size=19, min_size=13,
                     color=WHITE, bold=True, line_gap=4):
    """Sovittaa tekstin annettuun laatikkoon ilman päällekkäisyyksiä."""
    for size in range(start_size, min_size - 1, -1):
        face = font(size, bold)
        lines = wrapped_lines(text, face, rect.width)
        height = len(lines) * face.get_linesize() + max(0, len(lines)-1)*line_gap
        if height <= rect.height:
            break
    y = rect.top
    for line in lines:
        if line:
            surface.blit(face.render(line, True, color), (rect.left, y))
        y += face.get_linesize() + line_gap


class Button:
    def __init__(self, rect, label, action):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.action = action
        self.armed = False
        self.enabled = True

    def handle_event(self, event):
        if not self.enabled:
            self.armed = False
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.armed = self.rect.collidepoint(event.pos)
            return self.armed
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            activate = self.armed and self.rect.collidepoint(event.pos)
            self.armed = False
            if activate:
                self.action()
                return True
        return False

    def draw(self, surface):
        hover = self.rect.collidepoint(pygame.mouse.get_pos())
        bg = BUTTON_DOWN if self.armed else BUTTON_HOVER if hover else BUTTON
        fg = INK
        if not self.enabled:
            bg, fg = "#7f8997", "#d7dce4"
        pygame.draw.rect(surface, bg, self.rect, border_radius=5)
        pygame.draw.rect(surface, "#aab6c5", self.rect, 3, border_radius=5)
        draw_text(surface, self.label, self.rect.center, 16, fg, True, "center")


class TextInput:
    def __init__(self, rect):
        self.rect = pygame.Rect(rect)
        self.text = ""
        self.cursor_index = 0
        self.focused = True
        self.enabled = True
        self.cursor_visible = True
        self.last_blink = 0

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.focused = self.enabled and self.rect.collidepoint(event.pos)
            if self.focused:
                face=font(27,True)
                relative_x=max(0,event.pos[0]-(self.rect.left+14))
                self.cursor_index=min(
                    range(len(self.text)+1),
                    key=lambda index:abs(face.size(self.text[:index])[0]-relative_x),
                )
            return self.focused
        if not self.enabled or not self.focused or event.type != pygame.KEYDOWN:
            return False
        self.cursor_index=max(0,min(self.cursor_index,len(self.text)))
        if event.key == pygame.K_BACKSPACE:
            if self.cursor_index>0:
                self.text=(self.text[:self.cursor_index-1]
                           +self.text[self.cursor_index:])
                self.cursor_index-=1
        elif event.key == pygame.K_DELETE:
            if self.cursor_index<len(self.text):
                self.text=(self.text[:self.cursor_index]
                           +self.text[self.cursor_index+1:])
        elif event.key == pygame.K_LEFT:
            self.cursor_index=max(0,self.cursor_index-1)
        elif event.key == pygame.K_RIGHT:
            self.cursor_index=min(len(self.text),self.cursor_index+1)
        elif event.key == pygame.K_HOME:
            self.cursor_index=0
        elif event.key == pygame.K_END:
            self.cursor_index=len(self.text)
        elif event.key not in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if event.unicode and event.unicode in "0123456789.,-; " and len(self.text) < 60:
                self.text=(self.text[:self.cursor_index]+event.unicode
                           +self.text[self.cursor_index:])
                self.cursor_index+=len(event.unicode)
        return True

    def draw(self, surface):
        pygame.draw.rect(surface, "#071426", self.rect)
        pygame.draw.rect(surface, CYAN if self.focused else WHITE, self.rect, 3)
        image = font(27, True).render(self.text, True, WHITE)
        image.set_clip(pygame.Rect(0, 0, self.rect.width-28, self.rect.height))
        rect = image.get_rect(midleft=(self.rect.left+14, self.rect.centery))
        surface.blit(image, rect)
        now = pygame.time.get_ticks()
        if now-self.last_blink > 500:
            self.cursor_visible = not self.cursor_visible
            self.last_blink = now
        if self.focused and self.cursor_visible:
            self.cursor_index=max(0,min(self.cursor_index,len(self.text)))
            cursor_width=font(27,True).size(self.text[:self.cursor_index])[0]
            x = min(rect.left+cursor_width+2, self.rect.right-10)
            pygame.draw.line(surface, WHITE, (x, self.rect.top+12),
                             (x, self.rect.bottom-12), 2)


class PygameCanvas:
    """Tkinter Canvas -piirtojen pieni Pygame-sovitin."""
    def __init__(self, surface, viewport):
        self.surface = surface
        self.viewport = pygame.Rect(viewport)
        self.sx = self.viewport.width / 640
        self.sy = self.viewport.height / 520
        self.source_label_count = 0
        self.drawn_texts = []

    def p(self, x, y):
        return (round(self.viewport.left+x*self.sx),
                round(self.viewport.top+(y-80)*self.sy))

    @staticmethod
    def _coords(args):
        flattened = []
        pending = list(args)
        while pending:
            value = pending.pop(0)
            if isinstance(value, (tuple, list)):
                pending[0:0] = list(value)
            else:
                flattened.append(value)
        return [float(value) for value in flattened]

    def delete(self, *_):
        return None

    def create_line(self, *args, **kw):
        c = self._coords(args)
        pts = [self.p(c[i], c[i+1]) for i in range(0, len(c), 2)]
        if len(pts) > 1:
            pygame.draw.lines(self.surface, kw.get("fill", CYAN), False, pts,
                              max(1, round(kw.get("width", 2)*min(self.sx,self.sy))))
        return 0

    def create_rectangle(self, x1, y1, x2, y2, **kw):
        a, b = self.p(x1,y1), self.p(x2,y2)
        rect = pygame.Rect(min(a[0],b[0]), min(a[1],b[1]), abs(b[0]-a[0]), abs(b[1]-a[1]))
        fill = kw.get("fill")
        if fill:
            pygame.draw.rect(self.surface, fill, rect)
        outline = kw.get("outline")
        if outline:
            pygame.draw.rect(self.surface, outline, rect,
                             max(1, round(kw.get("width",1)*min(self.sx,self.sy))))
        return 0

    def create_oval(self, x1, y1, x2, y2, **kw):
        a, b = self.p(x1,y1), self.p(x2,y2)
        rect = pygame.Rect(min(a[0],b[0]), min(a[1],b[1]), max(1,abs(b[0]-a[0])), max(1,abs(b[1]-a[1])))
        if kw.get("fill"):
            pygame.draw.ellipse(self.surface, kw["fill"], rect)
        if kw.get("outline"):
            pygame.draw.ellipse(self.surface, kw["outline"], rect,
                                max(1,round(kw.get("width",1)*min(self.sx,self.sy))))
        return 0

    def create_polygon(self, *args, **kw):
        c = self._coords(args)
        pts = [self.p(c[i],c[i+1]) for i in range(0,len(c),2)]
        fill = kw.get("fill")
        outline = kw.get("outline")
        width = max(1, round(kw.get("width", 1) * min(self.sx, self.sy)))

        # Tkinter piirtää sekä täytön että reunaviivan, jos molemmat on annettu.
        # Pygamessa nämä täytyy piirtää erikseen. Vastusten suorakulmioissa on
        # tumma täyttö ja keltainen reunus, joten pelkkä täyttö teki ne
        # käytännössä näkymättömiksi.
        if fill:
            pygame.draw.polygon(self.surface, fill, pts)
        if outline:
            pygame.draw.polygon(self.surface, outline, pts, width)
        elif not fill:
            pygame.draw.polygon(self.surface, WHITE, pts, width)
        return 0

    def create_arc(self, *args, **kw):
        x1,y1,x2,y2 = self._coords(args)
        a,b=self.p(x1,y1),self.p(x2,y2)
        rect=pygame.Rect(min(a[0],b[0]),min(a[1],b[1]),abs(b[0]-a[0]),abs(b[1]-a[1]))
        start = -kw.get("start",0)*3.14159265/180
        stop = -(kw.get("start",0)+kw.get("extent",90))*3.14159265/180
        pygame.draw.arc(self.surface, kw.get("outline",WHITE), rect, min(start,stop), max(start,stop), max(1,kw.get("width",1)))
        return 0

    def create_text(self, x, y, **kw):
        raw_text=str(kw.get("text",""))
        normalized=" ".join(raw_text.split())
        component_match=re.match(r"^(Rs|R\d*|L\d*|C(?:g|\d*)|E\d+)\b",normalized)
        has_numeric_value=bool(re.search(r"[-+]?\d+(?:[.,]\d+)?",normalized))
        has_component_unit=bool(re.search(r"(?:Ω|[kmunµp]?F|[kmunµp]?H|[kmunµp]?V)\s*$",normalized))
        if component_match and has_numeric_value and has_component_unit:
            visible_text=component_match.group(1)
        elif re.fullmatch(r"[-+]?\d+(?:[.,]\d+)?\s*V",normalized):
            self.source_label_count+=1
            visible_text=f"E{self.source_label_count}"
        elif normalized=="KÄÄMI":
            visible_text="L"
        else:
            visible_text=raw_text
        kw["text"]=visible_text
        self.drawn_texts.append(visible_text)
        spec = kw.get("font", ("Arial", 12))
        size = abs(spec[1]) if isinstance(spec,(tuple,list)) and len(spec)>1 else 12
        bold = isinstance(spec,(tuple,list)) and any(str(v).lower()=="bold" for v in spec)
        image = font(size*min(self.sx,self.sy), bold).render(visible_text, True, kw.get("fill",WHITE))
        rect=image.get_rect()
        anchor=kw.get("anchor","center")
        mapping={"w":"midleft","e":"midright","n":"midtop","s":"midbottom","nw":"topleft","ne":"topright","sw":"bottomleft","se":"bottomright","center":"center"}
        setattr(rect,mapping.get(anchor,"center"),self.p(x,y))
        self.surface.blit(image,rect)
        return 0


def fmt(value):
    return f"{value:g}" if isinstance(value, (int,float)) else str(value)



def get_save_path() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home()))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", str(Path.home()/".local"/"share")))
    save_dir = base / "Sahkoseikkailu"
    save_dir.mkdir(parents=True, exist_ok=True)
    return save_dir / "sahkoseikkailu_save.json"

class ElectricityGame:
    def __init__(self, screen):
        self.screen=screen
        self.running=True
        self.task_number=1
        self.score=0
        self.highest_score=0
        self.unlocked_through=5
        self.scored_tasks=set()
        self.bonus_tasks=set()
        self.wrong_attempts=0
        self.hint_visible=False
        self.answer_visible=False
        self.bonus_visible=False
        self.bonus_choices=[]
        self.bonus_correct_index=None
        self.bonus_selected_index=None
        self.bonus_result="Valitse yksi vaihtoehto."
        self.bonus_result_color=MUTED
        self.information_kind=None
        self.information_scroll=0
        self.information_max_scroll=0
        self.presentation_mode=False
        self.presentation_dialog_visible=False
        self.presentation_snapshot=None
        self.progress_visible=False
        self.reset_dialog_visible=False
        self.save_confirmation_visible=False
        self.quit_dialog_visible=False
        self.unlock_notice_visible=False
        self.unlock_notice_text=""
        self.unlock_notice_title="UUSIA TEHTÄVIÄ AVATTU"
        self.final_exam_visible=False
        self.final_exam_index=0
        self.final_exam_selected=set()
        self.final_exam_points=[]
        self.final_exam_completed=False
        self.final_exam_passed=False
        self.final_exam_score=0.0
        self.final_exam_questions=[]
        self.final_exam_ready_notified=False
        self.victory_animation_start=None
        self.victory_particles=[]
        self.save_path=get_save_path()
        self.phase=0.0
        self.electrons=[i/12 for i in range(12)]
        self.branch_flow=0.0
        self.flash=0
        self.auto_advance_at=None
        self.auto_advance_from=None
        self.feedback="Syötä vastaus ja tarkista."
        self.feedback_color=MUTED
        self.input=TextInput((830,430,285,58))
        self.challenge=None
        self.task_menu_open=False
        self.task_menu_button=Button(
            (655, 18, 175, 32), "TEHTÄVÄ 1  ▼", self.toggle_task_menu
        )
        self.legacy_generator=legacy.ElectricityGame.__new__(legacy.ElectricityGame)
        self.buttons=[
            Button((830,495,285,47),"TARKISTA VASTAUS",self.check_answer),
            Button((830,549,285,40),"LISÄTEHTÄVÄ +5 P",self.open_bonus),
            Button((830,596,285,40),"VIHJE -5 P",self.open_hint),
            Button((830,643,285,45),"VASTAUS -10 P",self.open_answer),
        ]
        self.bonus_button=self.buttons[1]
        self.hint_button=self.buttons[2]
        self.close_hint_button=Button((520,475,200,44),"SULJE",self.close_hint)
        self.close_answer_button=Button((520,475,200,44),"SULJE",self.close_answer)
        self.check_bonus_button=Button((410,565,200,44),"TARKISTA",self.check_bonus_answer)
        self.close_bonus_button=Button((630,565,200,44),"SULJE",self.close_bonus)
        self.information_buttons=[
            Button((25,18,125,32),"SÄÄNNÖT",lambda:self.open_information("rules")),
            Button((25,58,125,32),"NEUVOJA",lambda:self.open_information("advice")),
            Button((175,18,145,32),"SUUREET",lambda:self.open_information("notation")),
        ]
        self.progress_button=Button((175,58,145,32),"EDISTYS",self.open_progress)
        self.save_button=Button((335,18,145,32),"TALLENNA",self.save_game)
        self.reset_button=Button((335,58,145,32),"ALOITA ALUSTA",self.open_reset_dialog)
        self.close_information_button=Button((520,650,200,42),"SULJE",self.close_information)
        self.close_progress_button=Button((520,625,200,42),"SULJE",self.close_progress)
        self.presentation_button=Button((495,18,145,32),"ESITTELYTILA",self.toggle_presentation)
        self.final_exam_button=Button((495,58,145,32),"LOPPUKOE",self.open_final_exam)
        self.activate_presentation_button=Button((410,475,200,46),"AKTIVOI",self.activate_presentation)
        self.cancel_presentation_button=Button((630,475,200,46),"PERUUTA",self.close_presentation_dialog)
        self.confirm_reset_button=Button((410,475,200,46),"ALOITA ALUSTA",self.reset_game)
        self.cancel_reset_button=Button((630,475,200,46),"PERUUTA",self.close_reset_dialog)
        self.close_save_confirmation_button=Button((520,465,200,46),"OK",self.close_save_confirmation)
        self.quit_save_button=Button((410,475,200,46),"KYLLÄ",self.confirm_quit_save)
        self.quit_without_save_button=Button((630,475,200,46),"EI",self.confirm_quit_without_save)
        self.close_unlock_notice_button=Button((520,510,200,46),"OK",self.close_unlock_notice)
        self.final_exam_submit_button=Button((410,620,200,46),"VASTAA",self.submit_final_exam_answer)
        self.final_exam_restart_button=Button((410,620,200,46),"YRITÄ UUDELLEEN",self.restart_final_exam)
        self.final_exam_close_button=Button((630,620,200,46),"SULJE",self.close_final_exam)
        self.concept_button=Button((1025,135,130,32),"LISÄTIETOA",self.open_concept_information)
        if "--self-test" in os.sys.argv:
            self.load_task(1)
        else:
            self.load_saved_game()

    def make_challenge(self, task_number):
        g=self.legacy_generator
        g.question_number=task_number-1
        g.next_question_job=None
        g.highest_unlocked=30
        g.scored_tasks=set()
        g.message=""
        g.finish_game=lambda:None
        g.task_is_unlocked=lambda _n:True
        g.show_challenge=lambda:None
        g.new_challenge(ignore_unlock=True)
        return g.challenge

    def task_is_unlocked(self,number):
        return 1<=number<=self.unlocked_through

    def refresh_unlocks(self):
        """Päivittää avatun tehtäväryhmän parhaiden saavutettujen pisteiden perusteella."""
        previous=self.unlocked_through
        if self.highest_score>=220:
            self.unlocked_through=30
        elif self.highest_score>=170:
            self.unlocked_through=26
        elif self.highest_score>=130:
            self.unlocked_through=20
        elif self.highest_score>=90:
            self.unlocked_through=15
        elif self.highest_score>=40:
            self.unlocked_through=10
        else:
            self.unlocked_through=5
        return self.unlocked_through if self.unlocked_through>previous else None

    def unlock_message(self, unlocked_through):
        messages={
            10:"Tehtävät 6–10 ovat nyt auki.",
            15:"Tehtävät 11–15 ovat nyt auki.",
            20:"Tehtävät 16–20 ovat nyt auki.",
            26:"Tehtävät 21–26 ovat nyt auki.",
            30:"Jokeritehtävät 27–30 ovat nyt auki.",
        }
        return messages.get(unlocked_through,"")

    def show_unlock_notice(self, unlocked_through):
        message=self.unlock_message(unlocked_through)
        if message:
            self.unlock_notice_title="UUSIA TEHTÄVIÄ AVATTU"
            self.unlock_notice_text=message
            self.unlock_notice_visible=True

    def close_unlock_notice(self):
        self.unlock_notice_visible=False

    def task_reward(self, number):
        return 20 if 27<=number<=30 else 10

    def next_unlock_target(self):
        """Palauttaa seuraavan vielä avaamattoman tehtäväryhmän pisterajan."""
        targets=((5,40),(10,90),(15,130),(20,170),(26,220))
        for unlocked_through,target in targets:
            if self.unlocked_through<=unlocked_through:
                return target
        return None

    def available_points_before_next_unlock(self):
        """Laskee avoinna olevista ratkaisemattomista tehtävistä vielä saatavat pisteet."""
        total=0
        for number in range(1,self.unlocked_through+1):
            if number in self.scored_tasks:
                continue
            remaining=self.task_reward(number)
            if number in self.bonus_tasks:
                remaining-=5
            total+=remaining
        return total

    def assistance_purchase_allowed(self, cost):
        """Estää avun ostamisen, jos seuraava avautumisraja muuttuisi mahdottomaksi."""
        if self.score<cost:
            return False,"insufficient"
        target=self.next_unlock_target()
        if target is None:
            return True,None
        future_points=self.available_points_before_next_unlock()
        if self.score-cost+future_points<target:
            return False,"reserved"
        return True,None

    def required_score_for_assistance(self, cost):
        """Pienin nykyinen pistemäärä, jolla apu voidaan ostaa turvallisesti."""
        target=self.next_unlock_target()
        if target is None:
            return cost
        future_points=self.available_points_before_next_unlock()
        return max(cost,target-future_points+cost)

    def assistance_block_message(self, cost, kind):
        allowed, _reason = self.assistance_purchase_allowed(cost)

        if allowed:
            return None

        required_score = self.required_score_for_assistance(cost)
        missing_points = max(1, required_score - self.score)

        return (
            f"Tarvitset vielä {missing_points} pistettä "
            f"avataksesi {kind}."
        )
    
    def all_tasks_completed(self):
        return len(self.scored_tasks)>=30

    def final_exam_available(self):
        return self.presentation_mode or self.all_tasks_completed()

    def announce_final_exam_ready(self):
        if self.presentation_mode or self.final_exam_ready_notified:
            return
        self.final_exam_ready_notified=True
        self.unlock_notice_title="LOPPUKOE ON VALMIS"
        self.unlock_notice_text=("Kaikki 30 tehtävää on ratkaistu. Loppukoe on nyt "
                                 "avattavissa yläreunan LOPPUKOE-painikkeesta.")
        self.unlock_notice_visible=True

    def prepare_final_exam_questions(self):
        questions=[]
        for question,choices,correct in FINAL_EXAM_QUESTIONS:
            order=list(range(4))
            random.shuffle(order)
            shuffled_choices=tuple(choices[index] for index in order)
            shuffled_correct={new_index for new_index,old_index in enumerate(order)
                              if old_index in correct}
            questions.append((question,shuffled_choices,shuffled_correct))
        random.shuffle(questions)
        return questions

    def open_final_exam(self):
        if not self.final_exam_available():
            self.feedback="Loppukoe avautuu, kun kaikki 30 tehtävää on ratkaistu."
            self.feedback_color=RED
            return
        self.start_final_exam()

    def start_final_exam(self):
        self.final_exam_visible=True
        self.final_exam_index=0
        self.final_exam_selected=set()
        self.final_exam_points=[]
        self.final_exam_completed=False
        self.final_exam_passed=False
        self.final_exam_score=0.0
        self.victory_animation_start=None
        self.victory_particles=[]
        self.final_exam_questions=self.prepare_final_exam_questions()

    def close_final_exam(self):
        self.final_exam_visible=False

    def restart_final_exam(self):
        self.start_final_exam()

    def score_final_exam_question(self, selected, correct):
        selected=set(selected)
        correct=set(correct)
        if len(correct)==1:
            if not selected:
                return 0.0
            return 1.0 if selected==correct else -0.5
        points=0.0
        for index in range(4):
            handled_correctly=(index in selected)==(index in correct)
            points+=0.25 if handled_correctly else -0.25
        return points

    def submit_final_exam_answer(self):
        if self.final_exam_completed:
            return
        _question,_choices,correct=self.final_exam_questions[self.final_exam_index]
        points=self.score_final_exam_question(self.final_exam_selected,correct)
        self.final_exam_points.append(points)
        self.final_exam_index+=1
        self.final_exam_selected=set()
        if self.final_exam_index>=len(self.final_exam_questions):
            self.final_exam_score=max(0.0,round(sum(self.final_exam_points),2))
            self.final_exam_completed=True
            self.final_exam_passed=self.final_exam_score>=8.0
            if self.final_exam_passed:
                self.start_victory_animation()
            self.save_game(show_confirmation=False)

    def start_victory_animation(self):
        """Käynnistää sähköteemaisen juhla-animaation loppukokeen läpäisystä."""
        self.victory_animation_start=pygame.time.get_ticks()
        self.victory_particles=[]
        colors=(CYAN,YELLOW,GREEN,WHITE)
        center_x,center_y=WIDTH/2,HEIGHT/2

        for _ in range(115):
            angle=random.uniform(0,math.tau)
            speed=random.uniform(110,430)
            self.victory_particles.append({
                "x":center_x+random.uniform(-25,25),
                "y":center_y+random.uniform(-20,20),
                "vx":math.cos(angle)*speed,
                "vy":math.sin(angle)*speed-random.uniform(20,130),
                "size":random.randint(2,6),
                "color":random.choice(colors),
                "born":random.uniform(0.0,0.7),
                "life":random.uniform(1.3,2.5),
            })

    def draw_victory_animation(self):
        """Piirtää animaation muun näkymän päälle jäädyttämättä tapahtumasilmukkaa."""
        if self.victory_animation_start is None:
            return

        elapsed=(pygame.time.get_ticks()-self.victory_animation_start)/1000
        duration=3.4
        if elapsed>=duration:
            self.victory_animation_start=None
            self.victory_particles=[]
            return

        overlay=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
        fade_in=min(1.0,elapsed/0.35)
        fade_out=min(1.0,(duration-elapsed)/0.55)
        visibility=max(0.0,min(fade_in,fade_out))
        overlay.fill((2,9,20,int(185*visibility)))

        center=(WIDTH//2,HEIGHT//2)
        for delay in (0.0,0.22,0.44):
            ring_time=elapsed-delay
            if 0<ring_time<1.45:
                progress=ring_time/1.45
                radius=int(35+progress*360)
                alpha=int(210*(1-progress)*visibility)
                color=pygame.Color(CYAN if delay!=0.22 else YELLOW)
                color.a=max(0,alpha)
                pygame.draw.circle(overlay,color,center,radius,max(2,int(7*(1-progress))))

        gravity=230
        for particle in self.victory_particles:
            age=elapsed-particle["born"]
            if age<0 or age>particle["life"]:
                continue
            life_progress=age/particle["life"]
            x=particle["x"]+particle["vx"]*age
            y=particle["y"]+particle["vy"]*age+0.5*gravity*age*age
            alpha=int(255*(1-life_progress)*visibility)
            color=pygame.Color(particle["color"])
            color.a=max(0,alpha)
            size=max(1,int(particle["size"]*(1-0.45*life_progress)))
            pygame.draw.circle(overlay,color,(round(x),round(y)),size)

        pulse=1.0+0.045*math.sin(elapsed*9)
        title_size=max(30,int(48*pulse))
        title_image=font(title_size,True).render("PELI LÄPÄISTY",True,GREEN)
        title_image.set_alpha(int(255*visibility))
        title_rect=title_image.get_rect(center=(center[0],center[1]-32))
        overlay.blit(title_image,title_rect)

        result_image=font(24,True).render(
            f"Loppukoe {self.final_exam_score:g}/10",
            True,
            WHITE,
        )
        result_image.set_alpha(int(255*visibility))
        result_rect=result_image.get_rect(center=(center[0],center[1]+35))
        overlay.blit(result_image,result_rect)

        self.screen.blit(overlay,(0,0))

    def load_task(self, number, ignore_unlock=False):
        self.auto_advance_at=None
        self.auto_advance_from=None
        number=max(1,min(30,number))
        if not ignore_unlock and not self.task_is_unlocked(number):
            self.feedback="Tämä tehtäväryhmä ei ole vielä avoinna. Kerää lisää pisteitä."
            self.feedback_color=RED
            self.task_menu_open=False
            return False
        self.task_number=number
        self.challenge=self.make_challenge(self.task_number)
        self.task_menu_open=False
        self.task_menu_button.label=f"TEHTÄVÄ {self.task_number}  ▼"
        self.input.text=""
        self.input.cursor_index=0
        self.input.focused=True
        self.wrong_attempts=0
        self.hint_visible=False
        self.answer_visible=False
        self.bonus_visible=False
        self.feedback=f"Tehtävä {self.task_number} avattiin uusilla lähtöarvoilla."
        self.feedback_color=GREEN
        self.update_bonus_button()
        return True

    def update_bonus_button(self):
        available=self.task_number not in self.bonus_tasks
        self.bonus_button.enabled=available
        if not available:
            self.bonus_button.label="LISÄTEHTÄVÄ TEHTY"
        elif self.task_number in self.scored_tasks:
            self.bonus_button.label="LISÄTEHTÄVÄ"
        else:
            self.bonus_button.label="LISÄTEHTÄVÄ +5 P"

    def open_bonus(self):
        if self.task_number in self.bonus_tasks:
            return
        template_number=legacy.TASK_TEMPLATE_ORDER[self.task_number-1]
        question,choices,correct_index=BONUS_QUESTION_OVERRIDES.get(
            template_number,legacy.BONUS_QUESTIONS[template_number]
        )
        shuffled=list(enumerate(choices))
        random.shuffle(shuffled)
        self.bonus_question=question
        self.bonus_choices=[choice for _original,choice in shuffled]
        self.bonus_correct_index=next(
            index for index,(original,_choice) in enumerate(shuffled)
            if original==correct_index
        )
        self.bonus_selected_index=None
        self.bonus_result="Valitse yksi vaihtoehto."
        self.bonus_result_color=MUTED
        self.check_bonus_button.enabled=True
        self.bonus_visible=True

    def close_bonus(self):
        self.bonus_visible=False

    def bonus_option_rects(self):
        return [pygame.Rect(330,335+index*62,580,50) for index in range(3)]

    def check_bonus_answer(self):
        if self.bonus_selected_index is None:
            self.bonus_result="Valitse ensin yksi vastausvaihtoehto."
            self.bonus_result_color=RED
            return
        if self.bonus_selected_index!=self.bonus_correct_index:
            self.bonus_result="Ei aivan. Tutki piiriä ja käsitteitä ja yritä uudelleen."
            self.bonus_result_color=RED
            return
        earned_points=0
        if self.task_number not in self.bonus_tasks:
            self.bonus_tasks.add(self.task_number)
            if self.task_number not in self.scored_tasks:
                earned_points=5
                self.score+=earned_points
                self.highest_score=max(self.highest_score,self.score)
                newly_unlocked=self.refresh_unlocks()
            else:
                newly_unlocked=None
        else:
            newly_unlocked=None
        if earned_points:
            remaining=self.task_reward(self.task_number)-5
            self.bonus_result=(f"Oikein! +5 pistettä. Tämän tehtävän varsinaisesta "
                               f"ratkaisusta saa vielä {remaining} pistettä.")
        else:
            self.bonus_result=("Oikein! Varsinainen tehtävä oli jo ratkaistu, "
                               "joten lisätehtävästä ei enää saa pisteitä.")
        if newly_unlocked:
            self.show_unlock_notice(newly_unlocked)
            self.bonus_result+=" "+self.unlock_message(newly_unlocked)
        self.bonus_result_color=GREEN
        self.check_bonus_button.enabled=False
        self.update_bonus_button()

    def toggle_task_menu(self):
        self.task_menu_open=not self.task_menu_open

    def task_menu_items(self):
        """Palauttaa kaikkien 30 tehtävän painikealueet (5 x 6)."""
        items=[]
        left,top=399,105
        cell_width,cell_height=76,38
        for number in range(1,31):
            column=(number-1)%5
            row=(number-1)//5
            rect=pygame.Rect(
                left+12+column*cell_width,
                top+48+row*cell_height,
                68,31,
            )
            items.append((number,rect))
        return items

    def open_hint(self):
        message=self.assistance_block_message(5,"vihjeen")
        if message:
            self.feedback=message
            self.feedback_color=RED
            return
        self.score-=5
        self.hint_visible=True

    def close_hint(self):
        self.hint_visible=False

    def open_answer(self):
        message=self.assistance_block_message(10,"oikean vastauksen")
        if message:
            self.feedback=message
            self.feedback_color=RED
            return
        self.score-=10
        self.answer_visible=True

    def close_answer(self):
        previous_challenge=self.challenge
        self.answer_visible=False
        self.load_task(self.task_number)
        # Arvotaan tarvittaessa uudelleen, kunnes vähintään yksi lähtöarvo
        # eroaa käyttäjälle juuri näytetystä tehtäväversiosta.
        while self.challenge==previous_challenge:
            self.challenge=self.make_challenge(self.task_number)
        self.feedback="Vastaus suljettiin. Tehtävään arvottiin uudet lähtöarvot."
        self.feedback_color=GREEN

    def formatted_answer(self):
        values="; ".join(f"{value:.1f}" for value in self.challenge.expected_values)
        return f"Oikea vastaus: {values} {self.challenge.answer_unit}"

    def open_information(self,kind):
        self.information_kind=kind
        self.information_scroll=0

    def close_information(self):
        self.information_kind=None
        self.information_scroll=0

    def concept_information_text(self):
        template_number=legacy.TASK_TEMPLATE_ORDER[self.task_number-1]
        section_keys=["electrical"]
        if template_number in legacy.NODE_INFO_TEMPLATES:
            section_keys.append("node")
        if template_number in legacy.THEVENIN_INFO_TEMPLATES:
            section_keys.append("thevenin")
        if template_number in legacy.ADMITTANCE_INFO_TEMPLATES:
            section_keys.append("admittance")
        if template_number in legacy.OPAMP_INFO_TEMPLATES:
            section_keys.append("opamp")
        if self.challenge.circuit_type=="lc_oscillator":
            section_keys.append("resonance")
        if self.challenge.circuit_type=="ac_parallel_lc":
            section_keys.append("parallel_resonance")
        return "\n\n".join(
            f"{CONCEPT_SECTIONS[key][0]}\n{CONCEPT_SECTIONS[key][1]}"
            for key in section_keys
        )

    def open_concept_information(self):
        self.open_information("concept")

    def open_progress(self):
        self.progress_visible=True

    def close_progress(self):
        self.progress_visible=False

    def task_progress_status(self,number):
        if number in self.scored_tasks:
            return "TEHTY"
        if self.task_is_unlocked(number):
            return "TEKEMÄTTÄ"
        return "LUKITTU"

    def save_game(self,show_confirmation=True):
        if self.presentation_mode:
            self.feedback="Esittelytilaa ei tallenneta. Palaa ensin pelitilaan."
            self.feedback_color=RED
            return False
        data={
            "version":1,
            "score":self.score,
            "highest_score":self.highest_score,
            "unlocked_through":self.unlocked_through,
            "scored_tasks":sorted(self.scored_tasks),
            "bonus_tasks":sorted(self.bonus_tasks),
            "task_number":self.task_number,
            "final_exam_completed":self.final_exam_completed,
            "final_exam_passed":self.final_exam_passed,
            "final_exam_score":self.final_exam_score,
            "final_exam_ready_notified":self.final_exam_ready_notified,
        }
        try:
            temporary_path=self.save_path.with_suffix(".tmp")
            temporary_path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
            temporary_path.replace(self.save_path)
        except OSError:
            self.feedback="Tallennus epäonnistui. Tarkista kansion kirjoitusoikeudet."
            self.feedback_color=RED
            return False
        self.feedback="Pisteet ja edistyminen tallennettiin."
        self.feedback_color=GREEN
        if show_confirmation:
            self.save_confirmation_visible=True
        return True

    def close_save_confirmation(self):
        self.save_confirmation_visible=False

    def confirm_quit_save(self):
        # Esittelytila on väliaikainen. Palautetaan ensin varsinainen peli,
        # jotta 1000 esittelypistettä eivät päädy tallennukseen.
        if self.presentation_mode:
            self.deactivate_presentation()
        if self.save_game(show_confirmation=False):
            self.quit_dialog_visible=False
            self.running=False
        else:
            self.quit_dialog_visible=False

    def confirm_quit_without_save(self):
        # Mitään ei kirjoiteta levylle. Seuraavalla käynnistyksellä peli
        # lukee edellisen tallennuksen tai aloittaa alusta, jos sitä ei ole.
        self.quit_dialog_visible=False
        self.running=False

    def load_saved_game(self):
        if not self.save_path.exists():
            self.load_task(1)
            return False
        try:
            data=json.loads(self.save_path.read_text(encoding="utf-8"))
            self.score=max(0,int(data.get("score",0)))
            self.highest_score=max(self.score,int(data.get("highest_score",self.score)))
            saved_unlock=int(data.get("unlocked_through",5))
            self.unlocked_through=max(5,min(30,saved_unlock))
            self.refresh_unlocks()
            self.scored_tasks={int(n) for n in data.get("scored_tasks",[]) if 1<=int(n)<=30}
            self.bonus_tasks={int(n) for n in data.get("bonus_tasks",[]) if 1<=int(n)<=30}
            self.final_exam_completed=bool(data.get("final_exam_completed",False))
            self.final_exam_passed=bool(data.get("final_exam_passed",False))
            self.final_exam_score=float(data.get("final_exam_score",0.0))
            self.final_exam_ready_notified=bool(data.get("final_exam_ready_notified",False))
            task_number=int(data.get("task_number",1))
            if not self.task_is_unlocked(task_number):
                task_number=1
            self.load_task(task_number)
            if self.all_tasks_completed() and not self.final_exam_passed:
                self.announce_final_exam_ready()
        except (OSError,ValueError,TypeError,json.JSONDecodeError):
            self.score=0
            self.highest_score=0
            self.unlocked_through=5
            self.scored_tasks=set()
            self.bonus_tasks=set()
            self.load_task(1)
            self.feedback="Tallennusta ei voitu lukea. Aloitettiin uusi peli."
            self.feedback_color=RED
            return False
        self.feedback="Tallennettu peli ladattiin."
        self.feedback_color=GREEN
        return True

    def open_reset_dialog(self):
        if self.presentation_mode:
            self.feedback="Palaa ensin pelitilaan ennen pelin nollaamista."
            self.feedback_color=RED
            return
        self.reset_dialog_visible=True

    def close_reset_dialog(self):
        self.reset_dialog_visible=False

    def reset_game(self):
        self.reset_dialog_visible=False
        self.score=0
        self.highest_score=0
        self.unlocked_through=5
        self.scored_tasks=set()
        self.bonus_tasks=set()
        self.final_exam_visible=False
        self.final_exam_completed=False
        self.final_exam_passed=False
        self.final_exam_score=0.0
        self.final_exam_points=[]
        self.final_exam_questions=[]
        self.final_exam_ready_notified=False
        self.load_task(1,ignore_unlock=True)
        self.feedback="Peli aloitettiin alusta. Pisteet ja edistyminen nollattiin."
        self.feedback_color=GREEN
        self.save_game(show_confirmation=False)
        self.feedback="Peli aloitettiin alusta. Pisteet ja edistyminen nollattiin."
        self.feedback_color=GREEN

    def toggle_presentation(self):
        if self.presentation_mode:
            self.deactivate_presentation()
        else:
            self.presentation_dialog_visible=True

    def close_presentation_dialog(self):
        self.presentation_dialog_visible=False

    def activate_presentation(self):
        if self.presentation_mode:
            return
        self.presentation_snapshot={
            "score":self.score,
            "highest_score":self.highest_score,
            "unlocked_through":self.unlocked_through,
            "scored_tasks":set(self.scored_tasks),
            "bonus_tasks":set(self.bonus_tasks),
            "task_number":self.task_number,
            "challenge":self.challenge,
            "wrong_attempts":self.wrong_attempts,
            "input_text":self.input.text,
            "input_cursor":self.input.cursor_index,
            "feedback":self.feedback,
            "feedback_color":self.feedback_color,
            "final_exam_completed":self.final_exam_completed,
            "final_exam_passed":self.final_exam_passed,
            "final_exam_score":self.final_exam_score,
            "final_exam_ready_notified":self.final_exam_ready_notified,
        }
        self.presentation_mode=True
        self.presentation_dialog_visible=False
        self.score=1000
        self.highest_score=1000
        self.unlocked_through=30
        self.scored_tasks=set()
        self.bonus_tasks=set()
        self.final_exam_visible=False
        self.presentation_button.label="PELITILA"
        self.update_bonus_button()
        self.feedback="Esittelytila on käytössä: 1000 pistettä ja kaikki tehtävät avoinna."
        self.feedback_color=GREEN

    def deactivate_presentation(self):
        snapshot=self.presentation_snapshot
        if not snapshot:
            return
        self.score=snapshot["score"]
        self.highest_score=snapshot["highest_score"]
        self.unlocked_through=snapshot["unlocked_through"]
        self.scored_tasks=set(snapshot["scored_tasks"])
        self.bonus_tasks=set(snapshot["bonus_tasks"])
        self.task_number=snapshot["task_number"]
        self.challenge=snapshot["challenge"]
        self.task_menu_button.label=f"TEHTÄVÄ {self.task_number}  ▼"
        self.wrong_attempts=snapshot["wrong_attempts"]
        self.input.text=snapshot["input_text"]
        self.input.cursor_index=snapshot["input_cursor"]
        self.feedback=snapshot["feedback"]
        self.feedback_color=snapshot["feedback_color"]
        self.final_exam_completed=snapshot["final_exam_completed"]
        self.final_exam_passed=snapshot["final_exam_passed"]
        self.final_exam_score=snapshot["final_exam_score"]
        self.final_exam_ready_notified=snapshot["final_exam_ready_notified"]
        self.final_exam_visible=False
        self.presentation_mode=False
        self.presentation_dialog_visible=False
        self.presentation_snapshot=None
        self.presentation_button.label="ESITTELYTILA"
        self.hint_visible=False
        self.answer_visible=False
        self.bonus_visible=False
        self.task_menu_open=False
        self.update_bonus_button()

    def prompt(self):
        c=self.challenge
        voltages,resistances=c.voltages,c.resistances
        if c.circuit_type.startswith("ac_"):
            kind=c.circuit_type
            names={
                "ac_resistive":"Resistiivinen vaihtovirtapiiri",
                "ac_series_rc":"RC-sarjapiiri",
                "ac_parallel_rc":"RC-rinnakkaispiiri",
                "ac_series_rlc":"RLC-sarjapiiri",
                "ac_capacitive":"Kapasitiivinen vaihtovirtapiiri",
                "ac_series_rl":"RL-sarjapiiri",
                "ac_parallel_rl":"RL-rinnakkaispiiri",
                "ac_parallel_rlc":"RLC-rinnakkaispiiri",
                "ac_inductive":"Induktiivinen vaihtovirtapiiri",
                "ac_series_lc":"LC-sarjapiiri",
                "ac_parallel_lc":"LC-rinnakkaispiiri",
                "ac_complex":"Yhdistetty sarja- ja rinnakkaispiiri",
            }
            component_parts=[]
            if kind=="ac_complex":
                r1,r2,r3=resistances
                c1,c2,c3=c.capacitances
                component_parts=[
                    f"R1={r1} Ω, R2={r2} Ω, R3={r3} Ω",
                    f"L1={c.inductance:g} H, L2={c.secondary_inductance:g} H",
                    f"C1={c1*1e6:g} µF, C2={c2*1e6:g} µF, C3={c3*1e6:g} µF",
                ]
            else:
                if kind not in {"ac_capacitive","ac_inductive","ac_series_lc","ac_parallel_lc"}:
                    component_parts.append(f"R={resistances[0]} Ω")
                if kind in {"ac_series_rlc","ac_series_rl","ac_parallel_rl","ac_parallel_rlc","ac_inductive","ac_series_lc","ac_parallel_lc"}:
                    component_parts.append(f"L={c.inductance:g} H")
                if kind in {"ac_series_rc","ac_parallel_rc","ac_series_rlc","ac_capacitive","ac_parallel_rlc","ac_series_lc","ac_parallel_lc"}:
                    component_parts.append(f"C={c.capacitances[0]*1e6:g} µF")
            components=", ".join(component_parts)
            task=(f"{names[kind]}. Vaihtojännite on {voltages[0]} V ja "
                  f"taajuus {c.frequency:g} Hz. {components}.\n\n"
                  "Laske piirissä kulkevan kokonaisvirran tehollisarvo kompleksisen "
                  "impedanssin avulla.")
        elif c.circuit_type=="three_source_mesh":
            e1,e2,e3=voltages
            r1,r2,r3,r4,r5=resistances
            task=(f"Kolmihaaraisessa piirissä E1={e1} V, E2={e2} V ja E3={e3} V. "
                  f"Vastukset ovat R1={r1} Ω, R2={r2} Ω, R3={r3} Ω, "
                  f"R4={r4} Ω ja R5={r5} Ω.\n\n"
                  "Laske haaravirrat järjestyksessä I1; I2; I3 Kirchhoffin lakien avulla. "
                  "Positiivinen suunta on kaikissa haaroissa yläsolmusta alasolmuun. "
                  "Negatiivinen vastaus tarkoittaa vastakkaista suuntaa.")
        elif c.circuit_type=="lc_oscillator":
            c1,c2=(value*1e9 for value in c.capacitances)
            task=("Operaatiovahvistin ylläpitää LC-verkon värähtelyä. "
                  f"L={c.inductance*1e3:g} mH, C1={c1:g} nF ja C2={c2:g} nF. "
                  f"Takaisinkytkentävastus R1={resistances[0]/1000:g} kΩ.\n\n"
                  "Laske oskillaattorin resonanssitaajuus. Käytä käämin kanssa "
                  "vaikuttavana kapasitanssina kondensaattorien sarjayhdistelmää.")
        elif c.circuit_type=="nodal_voltages":
            r1,r2,r3,r4,r5=resistances
            task=(f"U={voltages[0]} V. Vastukset ovat {r1} Ω, {r2} Ω, {r3} Ω, "
                  f"{r4} Ω ja {r5} Ω.\n\nLaske solmujännitteet V1 ja V2. "
                  "Anna vastaukset järjestyksessä V1; V2.")
        elif c.circuit_type=="bridge_currents":
            rs,r1,r2,r3,r4,r5=resistances
            task=(f"U={voltages[0]} V. Siltapiirin vastukset: Rs={rs} Ω, R1={r1} Ω, "
                  f"R2={r2} Ω, R3={r3} Ω, R4={r4} Ω ja R5={r5} Ω.\n\n"
                  "Laske haaravirtojen suuruudet järjestyksessä Is; I1; I2; I3; I4; I5.")
        elif c.circuit_type.startswith("thevenin_"):
            shunt,series,branch,output=resistances
            questions={
                "thevenin_voltage":"Määritä avoimen lähtöportin A–B Thévenin-jännite.",
                "thevenin_short_current":"Portti A–B oikosuljetaan. Laske oikosulkuvirta.",
                "thevenin_resistance":"Jännitelähde korvataan oikosululla. Laske portista A–B nähtävä vastus.",
                "thevenin_parallel":"Laske rinnankytkettyjen sisävastusten kokonaisresistanssi.",
                "thevenin_final":"Laske piirin Thévenin-vastus porttien A ja B väliltä.",
            }
            task=(f"U={voltages[0]} V, R1={shunt} Ω, R2={series} Ω, "
                  f"R3={branch} Ω ja R4={output} Ω.\n\n{questions[c.circuit_type]}")
        elif c.circuit_type=="coupled_lc":
            c1,c2=(value*1e6 for value in c.capacitances)
            cg=c.coupling_capacitance*1e6
            task=(f"Vaihtojännitelähde {voltages[0]} V / {c.frequency:g} Hz on kytketty "
                  f"oikean LC-piirin yli. L1={c.inductance:g} H, C1={c1:g} µF, "
                  f"L2={c.secondary_inductance:g} H, C2={c2:g} µF ja Cg={cg:g} µF.\n\n"
                  "Laske piirissä kulkeva kokonaisvirta.")
        elif c.circuit_type=="kirchhoff_parallel":
            r1,r2,r3=resistances
            task=(f"Jännitelähde {voltages[0]} V. Vastukset R1={r1} Ω, R2={r2} Ω "
                  f"ja R3={r3} Ω ovat rinnan.\n\n"
                  "Laske piirissä kulkeva kokonaisvirta Kirchhoffin solmulain avulla.")
        elif c.circuit_type=="kirchhoff":
            r1,r2,r3=resistances
            task=(f"Jännitelähde {voltages[0]} V. Vastukset R1={r1} Ω, R2={r2} Ω "
                  f"ja R3={r3} Ω.\n\nLaske piirissä kulkeva kokonaisvirta Kirchhoffin lakien avulla.")
        elif c.capacitances:
            c1,c2=(value*1e6 for value in c.capacitances)
            task=(f"Vaihtojännite {voltages[0]} V, vastus {resistances[0]} Ω, "
                  f"kondensaattorit {c1:g} µF ja {c2:g} µF rinnan sekä taajuus "
                  f"{c.frequency:g} Hz.\n\nLaske piirissä kulkeva virta.")
        elif c.inductance:
            task=(f"Vaihtojännite {voltages[0]} V, vastus {resistances[0]} Ω, "
                  f"käämi {c.inductance:g} H ja taajuus {c.frequency:g} Hz.\n\n"
                  "Laske piirissä kulkeva virta.")
        elif len(voltages)==1:
            task=(f"Jännite on {voltages[0]} V ja vastus {resistances[0]} Ω.\n\n"
                  "Laske piirissä kulkeva virta.")
        elif len(resistances)==1:
            task=(f"Sarjassa on kaksi lähdettä: {voltages[0]} V ja {voltages[1]} V. "
                  f"Vastus on {resistances[0]} Ω.\n\nLaske piirissä kulkeva virta.")
        elif len(resistances)==2:
            r1,r2=resistances
            task=(f"Kaksi lähdettä: {voltages[0]} V ja {voltages[1]} V. "
                  f"Vastukset {r1} Ω ja {r2} Ω ovat rinnan.\n\n"
                  "Laske piirissä kulkeva kokonaisvirta.")
        else:
            r1,r2,r3=resistances
            task=(f"Kaksi {voltages[0]} V lähdettä on rinnan. Vastukset {r1} Ω, "
                  f"{r2} Ω ja {r3} Ω ovat rinnan.\n\nLaske piirissä kulkeva kokonaisvirta.")
        answer_instruction="Anna vastaus yhden desimaalin tarkkuudella."
        if len(c.expected_values)>1:
            answer_instruction+=(" Erota arvot puolipisteillä; välilyönnit "
                                 "puolipisteiden jälkeen ovat vapaaehtoisia.")
        return task+"\n\n"+answer_instruction

    def check_answer(self):
        raw=self.input.text.strip().replace(",",".")
        try:
            values=tuple(float(x.strip()) for x in raw.split(";") if x.strip())
        except ValueError:
            values=()
        expected=tuple(round(v,1) for v in self.challenge.expected_values)
        if len(values)==len(expected) and all(abs(a-b)<=0.051 for a,b in zip(values,expected)):
            unlocked_message=""
            earned_points=0
            if self.task_number not in self.scored_tasks:
                self.scored_tasks.add(self.task_number)
                full_reward=self.task_reward(self.task_number)
                earned_points=full_reward-5 if self.task_number in self.bonus_tasks else full_reward
                self.score+=earned_points
                self.highest_score=max(self.highest_score,self.score)
                newly_unlocked=self.refresh_unlocks()
                if newly_unlocked:
                    self.show_unlock_notice(newly_unlocked)
                    unlocked_message=" "+self.unlock_message(newly_unlocked)
            self.feedback=(f"Oikein! Tehtävä ratkaistu. +{earned_points} pistettä."
                           if earned_points else "Oikein! Tehtävä oli jo ratkaistu.")
            self.feedback+=unlocked_message
            self.feedback_color=GREEN
            self.flash=12
            self.bonus_visible=False
            self.update_bonus_button()
            if self.all_tasks_completed() and not self.final_exam_passed:
                self.announce_final_exam_ready()
            next_task=self.task_number+1
            if next_task<=30 and self.task_is_unlocked(next_task):
                self.auto_advance_from=self.task_number
                self.auto_advance_at=pygame.time.get_ticks()+1100
        else:
            self.wrong_attempts+=1
            if self.wrong_attempts>=3:
                self.load_task(self.task_number)
                self.feedback="Kolme väärää vastausta. Tehtävään arvottiin uudet lähtöarvot."
                self.feedback_color=RED
            else:
                attempts_left=3-self.wrong_attempts
                self.feedback=(f"Ei aivan. Tarkista arvot ja niiden järjestys. "
                               f"Yrityksiä jäljellä: {attempts_left}.")
                self.feedback_color=RED
            self.flash=-12
        self.input.focused=True

    def handle_event(self,event):
        if event.type==pygame.QUIT:
            self.quit_dialog_visible=True
            return
        if event.type==pygame.KEYDOWN and event.key==pygame.K_ESCAPE:
            if self.quit_dialog_visible:
                self.quit_dialog_visible=False
            elif self.save_confirmation_visible:
                self.close_save_confirmation()
            elif self.reset_dialog_visible:
                self.close_reset_dialog()
            elif self.presentation_dialog_visible:
                self.close_presentation_dialog()
            elif self.final_exam_visible:
                self.close_final_exam()
            elif self.unlock_notice_visible:
                self.close_unlock_notice()
            elif self.progress_visible:
                self.close_progress()
            elif self.information_kind:
                self.close_information()
            elif self.bonus_visible:
                self.close_bonus()
            elif self.answer_visible:
                self.close_answer()
            elif self.hint_visible:
                self.close_hint()
            elif self.task_menu_open:
                self.task_menu_open=False
            else:
                self.running=False
            return

        if self.quit_dialog_visible:
            self.quit_save_button.handle_event(event)
            self.quit_without_save_button.handle_event(event)
            return

        if self.save_confirmation_visible:
            self.close_save_confirmation_button.handle_event(event)
            return

        if self.final_exam_visible:
            if not self.final_exam_completed and event.type==pygame.MOUSEBUTTONUP and event.button==1:
                for index,rect in enumerate(self.final_exam_option_rects()):
                    if rect.collidepoint(event.pos):
                        _question,_choices,correct=self.final_exam_questions[self.final_exam_index]
                        if len(correct)==1:
                            self.final_exam_selected={index}
                        elif index in self.final_exam_selected:
                            self.final_exam_selected.remove(index)
                        else:
                            self.final_exam_selected.add(index)
                        return
            if self.final_exam_completed:
                if self.final_exam_passed:
                    self.final_exam_close_button.handle_event(event)
                else:
                    self.final_exam_restart_button.handle_event(event)
                    self.final_exam_close_button.handle_event(event)
            else:
                self.final_exam_submit_button.handle_event(event)
            return

        if self.unlock_notice_visible:
            self.close_unlock_notice_button.handle_event(event)
            return

        if self.reset_dialog_visible:
            self.confirm_reset_button.handle_event(event)
            self.cancel_reset_button.handle_event(event)
            return

        if self.progress_visible:
            self.close_progress_button.handle_event(event)
            return

        if self.presentation_dialog_visible:
            self.activate_presentation_button.handle_event(event)
            self.cancel_presentation_button.handle_event(event)
            return

        if self.bonus_visible:
            if event.type==pygame.MOUSEBUTTONUP and event.button==1 and self.check_bonus_button.enabled:
                for index,rect in enumerate(self.bonus_option_rects()):
                    if rect.collidepoint(event.pos):
                        self.bonus_selected_index=index
                        self.bonus_result="Valittu. Tarkista vastaus."
                        self.bonus_result_color=MUTED
                        return
            self.check_bonus_button.handle_event(event)
            self.close_bonus_button.handle_event(event)
            return

        if self.information_kind:
            if event.type==pygame.MOUSEWHEEL:
                self.information_scroll=max(0,min(
                    self.information_max_scroll,
                    self.information_scroll-event.y*36,
                ))
            elif event.type==pygame.KEYDOWN and event.key in (pygame.K_UP,pygame.K_DOWN,pygame.K_PAGEUP,pygame.K_PAGEDOWN):
                direction=-1 if event.key in (pygame.K_UP,pygame.K_PAGEUP) else 1
                step=36 if event.key in (pygame.K_UP,pygame.K_DOWN) else 260
                self.information_scroll=max(0,min(
                    self.information_max_scroll,
                    self.information_scroll+direction*step,
                ))
            self.close_information_button.handle_event(event)
            return

        # Vihjeikkuna on modaalinen: sen ollessa auki muut painikkeet ja
        # vastauskenttä eivät reagoi napsautuksiin.
        if self.hint_visible:
            self.close_hint_button.handle_event(event)
            return
        if self.answer_visible:
            self.close_answer_button.handle_event(event)
            return

        for button in self.information_buttons:
            if button.handle_event(event):
                return
        if self.progress_button.handle_event(event):
            return
        if self.save_button.handle_event(event):
            return
        if self.reset_button.handle_event(event):
            return
        if self.concept_button.handle_event(event):
            return
        if self.presentation_button.handle_event(event):
            return
        if self.final_exam_button.handle_event(event):
            return

        # Tehtävävalikko käsitellään ennen piirissä olevia muita
        # painikkeita. Näin valikon jokainen kohta reagoi koko alueeltaan.
        if self.task_menu_open and event.type in (pygame.MOUSEBUTTONDOWN,pygame.MOUSEBUTTONUP) and event.button==1:
            if event.type==pygame.MOUSEBUTTONUP:
                for number,rect in self.task_menu_items():
                    if rect.collidepoint(event.pos):
                        self.load_task(number)
                        return
            if not self.task_menu_button.rect.collidepoint(event.pos):
                if event.type==pygame.MOUSEBUTTONUP:
                    self.task_menu_open=False
                return

        if self.task_menu_button.handle_event(event):
            return
        if event.type==pygame.KEYDOWN and event.key in (pygame.K_RETURN,pygame.K_KP_ENTER) and self.input.focused:
            self.check_answer(); return
        consumed=False
        for b in self.buttons: consumed=b.handle_event(event) or consumed
        if not consumed: self.input.handle_event(event)

    def update(self,dt):
        if (self.auto_advance_at is not None
                and pygame.time.get_ticks()>=self.auto_advance_at):
            next_task=self.auto_advance_from+1
            if (self.task_number==self.auto_advance_from
                    and self.task_is_unlocked(next_task)):
                self.load_task(next_task)
            else:
                self.auto_advance_at=None
                self.auto_advance_from=None

        # Vaihetta ei kierretä takaisin nollaan. Jatkuva vaihe estää
        # vaihtovirtapiirin animaatiota nytkähtämästä jakson vaihtuessa.
        self.phase += dt * 1.5

        # Sama liikelogiikka kuin alkuperäisessä Tkinter-versiossa:
        # vaihtovirralla pallot hidastuvat, pysähtyvät ja vaihtavat suuntaa.
        speed_per_second=(0.003+min(abs(self.challenge.current),5)*0.0015)*30
        flow_direction=math.cos(self.phase*2) if self.challenge.frequency else 1.0
        if abs(flow_direction)<0.02:
            flow_direction=0.0
        signed_step=speed_per_second*flow_direction*dt
        self.electrons=[(position+signed_step)%1 for position in self.electrons]
        self.branch_flow=(self.branch_flow+signed_step*210)%180

        if self.flash>0:
            self.flash-=1
        elif self.flash<0:
            self.flash+=1

    def draw_circuit(self, rect):
        adapter=PygameCanvas(self.screen,rect)
        renderer=legacy.ElectricityGame.__new__(legacy.ElectricityGame)
        renderer.canvas=adapter
        renderer.challenge=self.challenge
        renderer.question_number=self.task_number
        renderer.running=True
        renderer.phase=self.phase
        renderer.branch_flow=self.branch_flow
        renderer.particles=[]
        renderer.electrons=list(self.electrons)
        renderer.draw_circuit()
        self.last_circuit_texts=list(adapter.drawn_texts)
        return adapter

    def draw_task_menu(self):
        if not self.task_menu_open:
            return
        panel=pygame.Rect(399,105,404,292)
        shadow=panel.move(5,6)
        pygame.draw.rect(self.screen,"#020914",shadow,border_radius=8)
        pygame.draw.rect(self.screen,PANEL,panel,border_radius=8)
        pygame.draw.rect(self.screen,PANEL_BORDER,panel,3,border_radius=8)
        draw_text(self.screen,"VALITSE TEHTÄVÄ",(panel.centerx,panel.top+25),18,CYAN,True,"center")
        mouse=pygame.mouse.get_pos()
        for number,rect in self.task_menu_items():
            selected=number==self.task_number
            hover=rect.collidepoint(mouse)
            unlocked=self.task_is_unlocked(number)
            bg=("#ffd34f" if selected else
                BUTTON_HOVER if unlocked and hover else
                BUTTON if unlocked else "#526174")
            # Painikkeet ovat vaaleita, joten kaikkien tehtävänumeroiden pitää
            # olla tummia myös silloin, kun painike ei ole valittu tai osoittimen alla.
            fg=INK if unlocked else "#aeb9c7"
            pygame.draw.rect(self.screen,bg,rect,border_radius=4)
            pygame.draw.rect(self.screen,"#aab6c5" if unlocked else "#657286",rect,2,border_radius=4)
            draw_text(self.screen,str(number),rect.center,15,fg,True,"center")

    def draw_hint_window(self):
        if not self.hint_visible:
            return
        overlay=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
        overlay.fill((0,0,0,165))
        self.screen.blit(overlay,(0,0))
        panel=pygame.Rect(270,205,700,335)
        pygame.draw.rect(self.screen,"#020914",panel.move(7,8),border_radius=12)
        pygame.draw.rect(self.screen,PANEL,panel,border_radius=12)
        pygame.draw.rect(self.screen,YELLOW,panel,3,border_radius=12)
        draw_text(self.screen,f"VIHJE – TEHTÄVÄ {self.task_number}",
                  (panel.centerx,panel.top+38),24,YELLOW,True,"center")
        draw_fitted_text(self.screen,HINTS[self.task_number],
                         pygame.Rect(panel.left+55,panel.top+90,panel.width-110,130),
                         21,15,WHITE,True,6)
        self.close_hint_button.draw(self.screen)
        draw_text(self.screen,"Esc = sulje",(panel.centerx,panel.bottom-10),
                  13,MUTED,False,"midbottom")

    def draw_bonus_window(self):
        if not self.bonus_visible:
            return
        overlay=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
        overlay.fill((0,0,0,175))
        self.screen.blit(overlay,(0,0))
        panel=pygame.Rect(250,105,740,565)
        pygame.draw.rect(self.screen,"#020914",panel.move(7,8),border_radius=12)
        pygame.draw.rect(self.screen,PANEL,panel,border_radius=12)
        pygame.draw.rect(self.screen,CYAN,panel,3,border_radius=12)
        draw_text(self.screen,f"LISÄTEHTÄVÄ – TEHTÄVÄ {self.task_number}",
                  (panel.centerx,panel.top+35),24,CYAN,True,"center")
        draw_fitted_text(self.screen,self.bonus_question,
                         pygame.Rect(panel.left+65,panel.top+80,panel.width-130,115),
                         20,14,WHITE,True,5)
        mouse=pygame.mouse.get_pos()
        for index,(choice,rect) in enumerate(zip(self.bonus_choices,self.bonus_option_rects())):
            selected=index==self.bonus_selected_index
            bg="#244d72" if selected else "#1a3858" if rect.collidepoint(mouse) else "#132d4b"
            pygame.draw.rect(self.screen,bg,rect,border_radius=7)
            pygame.draw.rect(self.screen,YELLOW if selected else PANEL_BORDER,rect,3,border_radius=7)
            circle=(rect.left+22,rect.centery)
            pygame.draw.circle(self.screen,WHITE,circle,9,2)
            if selected:
                pygame.draw.circle(self.screen,YELLOW,circle,5)
            draw_fitted_text(self.screen,choice,
                             pygame.Rect(rect.left+44,rect.top+7,rect.width-56,rect.height-12),
                             16,12,WHITE,False,2)
        draw_fitted_text(self.screen,self.bonus_result,
                         pygame.Rect(panel.left+80,panel.top+410,panel.width-160,42),
                         15,11,self.bonus_result_color,False,2)
        self.check_bonus_button.draw(self.screen)
        self.close_bonus_button.draw(self.screen)
        draw_text(self.screen,"Esc = sulje",(panel.centerx,panel.bottom-8),
                  13,MUTED,False,"midbottom")

    def draw_answer_window(self):
        if not self.answer_visible:
            return
        overlay=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
        overlay.fill((0,0,0,165))
        self.screen.blit(overlay,(0,0))
        panel=pygame.Rect(270,205,700,335)
        pygame.draw.rect(self.screen,"#020914",panel.move(7,8),border_radius=12)
        pygame.draw.rect(self.screen,PANEL,panel,border_radius=12)
        pygame.draw.rect(self.screen,GREEN,panel,3,border_radius=12)
        draw_text(self.screen,f"OIKEA VASTAUS – TEHTÄVÄ {self.task_number}",
                  (panel.centerx,panel.top+38),24,GREEN,True,"center")
        draw_fitted_text(self.screen,self.formatted_answer(),
                         pygame.Rect(panel.left+55,panel.top+105,panel.width-110,100),
                         25,16,WHITE,True,6)
        draw_fitted_text(self.screen,
                         "Kun suljet tämän ikkunan, tehtävään arvotaan uudet lähtöarvot.",
                         pygame.Rect(panel.left+80,panel.top+210,panel.width-160,45),
                         15,12,MUTED,False,3)
        self.close_answer_button.draw(self.screen)
        draw_text(self.screen,"Esc = sulje",(panel.centerx,panel.bottom-10),
                  13,MUTED,False,"midbottom")

    def draw_information_window(self):
        if not self.information_kind:
            return
        if self.information_kind=="rules":
            title,body="PELIN SÄÄNNÖT",RULES_TEXT
        elif self.information_kind=="advice":
            title,body="NEUVOJA PELAAMISEEN",ADVICE_TEXT
        elif self.information_kind=="notation":
            title,body="SÄHKÖOPIN SUUREET JA MERKINNÄT",NOTATION_TEXT
        else:
            title,body=f"LISÄTIETOA – TEHTÄVÄ {self.task_number}",self.concept_information_text()
        overlay=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
        overlay.fill((0,0,0,175))
        self.screen.blit(overlay,(0,0))
        panel=pygame.Rect(180,55,880,655)
        pygame.draw.rect(self.screen,"#020914",panel.move(7,8),border_radius=12)
        pygame.draw.rect(self.screen,PANEL,panel,border_radius=12)
        pygame.draw.rect(self.screen,CYAN,panel,3,border_radius=12)
        draw_text(self.screen,title,(panel.centerx,panel.top+35),25,CYAN,True,"center")

        text_rect=pygame.Rect(panel.left+55,panel.top+80,panel.width-110,495)
        face=font(17,False)
        lines=wrapped_lines(body,face,text_rect.width-12)
        line_height=face.get_linesize()+4
        content_height=len(lines)*line_height
        self.information_max_scroll=max(0,content_height-text_rect.height)
        self.information_scroll=min(self.information_scroll,self.information_max_scroll)
        old_clip=self.screen.get_clip()
        self.screen.set_clip(text_rect)
        y=text_rect.top-self.information_scroll
        for line in lines:
            if line:
                is_heading=line.isupper() and not line.startswith("-")
                image=font(17,is_heading).render(line,True,YELLOW if is_heading else WHITE)
                self.screen.blit(image,(text_rect.left,y))
            y+=line_height
        self.screen.set_clip(old_clip)

        if self.information_max_scroll:
            track=pygame.Rect(panel.right-28,text_rect.top,7,text_rect.height)
            pygame.draw.rect(self.screen,"#071426",track,border_radius=4)
            thumb_height=max(35,round(track.height*text_rect.height/content_height))
            travel=track.height-thumb_height
            thumb_y=track.top+round(travel*self.information_scroll/self.information_max_scroll)
            pygame.draw.rect(self.screen,CYAN,(track.left,thumb_y,track.width,thumb_height),border_radius=4)
            draw_text(self.screen,"Vieritä hiirellä tai nuolinäppäimillä",
                      (panel.left+55,panel.bottom-52),13,MUTED)
        self.close_information_button.draw(self.screen)

    def final_exam_option_rects(self):
        return [pygame.Rect(300,285+index*68,640,54) for index in range(4)]

    def draw_unlock_notice(self):
        if not self.unlock_notice_visible:
            return
        overlay=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
        overlay.fill((0,0,0,185)); self.screen.blit(overlay,(0,0))
        panel=pygame.Rect(300,215,640,350)
        pygame.draw.rect(self.screen,"#020914",panel.move(7,8),border_radius=12)
        pygame.draw.rect(self.screen,PANEL,panel,border_radius=12)
        pygame.draw.rect(self.screen,GREEN,panel,3,border_radius=12)
        draw_text(self.screen,self.unlock_notice_title,(panel.centerx,panel.top+65),27,GREEN,True,"center")
        draw_fitted_text(self.screen,self.unlock_notice_text,pygame.Rect(panel.left+75,panel.top+125,panel.width-150,100),25,18,WHITE,True,5)
        self.close_unlock_notice_button.draw(self.screen)

    def draw_final_exam(self):
        if not self.final_exam_visible:
            return
        if not self.final_exam_questions:
            self.final_exam_questions=self.prepare_final_exam_questions()
        overlay=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
        overlay.fill((0,0,0,205)); self.screen.blit(overlay,(0,0))
        panel=pygame.Rect(180,45,880,680)
        pygame.draw.rect(self.screen,"#020914",panel.move(7,8),border_radius=12)
        pygame.draw.rect(self.screen,PANEL,panel,border_radius=12)
        pygame.draw.rect(self.screen,CYAN,panel,3,border_radius=12)
        draw_text(self.screen,"LOPPUKOE",(panel.centerx,panel.top+35),28,CYAN,True,"center")
        if self.final_exam_completed:
            result_color=GREEN if self.final_exam_passed else RED
            title="PELI LÄPÄISTY" if self.final_exam_passed else "LOPPUKOE EI MENNYT LÄPI"
            draw_text(self.screen,title,(panel.centerx,panel.top+120),30,result_color,True,"center")
            draw_text(self.screen,f"Tulos: {self.final_exam_score:g}/10",(panel.centerx,panel.top+195),28,WHITE,True,"center")
            message=("Ratkaisit kaikki tehtävät ja sait loppukokeesta vähintään 8 pistettä."
                     if self.final_exam_passed else
                     "Läpäisyyn tarvitaan vähintään 8/10 pistettä. Voit yrittää loppukoetta uudelleen.")
            draw_fitted_text(self.screen,message,pygame.Rect(panel.left+120,panel.top+250,panel.width-240,130),22,16,WHITE,False,6)
            if not self.final_exam_passed:
                self.final_exam_restart_button.draw(self.screen)
            self.final_exam_close_button.draw(self.screen)
            return
        question,choices,correct=self.final_exam_questions[self.final_exam_index]
        draw_text(self.screen,f"Kysymys {self.final_exam_index+1}/10",(panel.centerx,panel.top+80),17,YELLOW,True,"center")
        instruction=("Valitse yksi vaihtoehto." if len(correct)==1 else "Valitse kaikki oikeat vaihtoehdot.")
        draw_fitted_text(self.screen,question,pygame.Rect(panel.left+100,panel.top+115,panel.width-200,90),23,16,WHITE,True,5)
        draw_text(self.screen,instruction,(panel.centerx,panel.top+220),15,MUTED,False,"center")
        for index,(choice,rect) in enumerate(zip(choices,self.final_exam_option_rects())):
            selected=index in self.final_exam_selected
            bg="#1f5a4a" if selected else "#172b44"
            border=GREEN if selected else PANEL_BORDER
            pygame.draw.rect(self.screen,bg,rect,border_radius=7)
            pygame.draw.rect(self.screen,border,rect,3,border_radius=7)
            box=pygame.Rect(rect.left+14,rect.centery-11,22,22)
            pygame.draw.rect(self.screen,"#081421",box,border_radius=3)
            pygame.draw.rect(self.screen,border,box,2,border_radius=3)
            if selected:
                draw_text(self.screen,"✓",box.center,18,GREEN,True,"center")
            draw_fitted_text(self.screen,choice,pygame.Rect(rect.left+50,rect.top+7,rect.width-62,rect.height-14),17,12,WHITE,False,2)
        self.final_exam_submit_button.draw(self.screen)

    def draw_progress_window(self):
        if not self.progress_visible:
            return
        overlay=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
        overlay.fill((0,0,0,175))
        self.screen.blit(overlay,(0,0))
        panel=pygame.Rect(210,70,820,620)
        pygame.draw.rect(self.screen,"#020914",panel.move(7,8),border_radius=12)
        pygame.draw.rect(self.screen,PANEL,panel,border_radius=12)
        pygame.draw.rect(self.screen,CYAN,panel,3,border_radius=12)
        draw_text(self.screen,"EDISTYMINEN",(panel.centerx,panel.top+35),26,CYAN,True,"center")
        completed=sum(number in self.scored_tasks for number in range(1,31))
        draw_text(self.screen,f"Ratkaistu {completed}/30 tehtävää",
                  (panel.centerx,panel.top+70),17,WHITE,True,"center")
        if self.final_exam_passed:
            draw_text(self.screen,f"Loppukoe läpäisty: {self.final_exam_score:g}/10",
                      (panel.centerx,panel.top+98),15,GREEN,True,"center")
        elif self.final_exam_completed:
            draw_text(self.screen,f"Loppukoe: {self.final_exam_score:g}/10",
                      (panel.centerx,panel.top+98),15,YELLOW,True,"center")

        colors={"TEHTY":GREEN,"TEKEMÄTTÄ":YELLOW,"LUKITTU":"#69788b"}
        left,top=270,180
        cell_width,cell_height=118,72
        for number in range(1,31):
            column=(number-1)%6
            row=(number-1)//6
            rect=pygame.Rect(left+column*cell_width,top+row*cell_height,106,60)
            status=self.task_progress_status(number)
            border=colors[status]
            bg="#173a31" if status=="TEHTY" else "#3b3420" if status=="TEKEMÄTTÄ" else "#263242"
            pygame.draw.rect(self.screen,bg,rect,border_radius=7)
            pygame.draw.rect(self.screen,border,rect,3,border_radius=7)
            draw_text(self.screen,f"TEHTÄVÄ {number}",(rect.centerx,rect.top+11),14,WHITE,True,"midtop")
            draw_text(self.screen,status,(rect.centerx,rect.bottom-10),12,border,True,"midbottom")

        legend_y=panel.bottom-110
        legend_items=(("TEHTY",GREEN),("TEKEMÄTTÄ",YELLOW),("LUKITTU","#69788b"))
        x=panel.left+80
        for label,color in legend_items:
            pygame.draw.circle(self.screen,color,(x,legend_y),7)
            draw_text(self.screen,label,(x+14,legend_y),13,WHITE,True,"midleft")
            x+=190
        self.close_progress_button.draw(self.screen)

    def draw_presentation_dialog(self):
        if not self.presentation_dialog_visible:
            return
        overlay=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
        overlay.fill((0,0,0,175))
        self.screen.blit(overlay,(0,0))
        panel=pygame.Rect(270,185,700,355)
        pygame.draw.rect(self.screen,"#020914",panel.move(7,8),border_radius=12)
        pygame.draw.rect(self.screen,PANEL,panel,border_radius=12)
        pygame.draw.rect(self.screen,YELLOW,panel,3,border_radius=12)
        draw_text(self.screen,"ESITTELYTILA",(panel.centerx,panel.top+42),26,YELLOW,True,"center")
        explanation=("Esittelytila on tarkoitettu pelin ominaisuuksien esittelemiseen. "
                     "Saat tilapäisesti 1000 pistettä ja kaikki 30 tehtävää avautuvat. "
                     "Esittelytilassa tehdyt suoritukset eivät muuta varsinaisen pelin etenemistä. "
                     "Voit palata koska tahansa PELITILA-painikkeella.")
        draw_fitted_text(self.screen,explanation,
                         pygame.Rect(panel.left+65,panel.top+100,panel.width-130,180),
                         19,14,WHITE,False,6)
        self.activate_presentation_button.draw(self.screen)
        self.cancel_presentation_button.draw(self.screen)

    def draw_reset_dialog(self):
        if not self.reset_dialog_visible:
            return
        overlay=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
        overlay.fill((0,0,0,175))
        self.screen.blit(overlay,(0,0))
        panel=pygame.Rect(270,185,700,355)
        pygame.draw.rect(self.screen,"#020914",panel.move(7,8),border_radius=12)
        pygame.draw.rect(self.screen,PANEL,panel,border_radius=12)
        pygame.draw.rect(self.screen,RED,panel,3,border_radius=12)
        draw_text(self.screen,"ALOITA ALUSTA?",(panel.centerx,panel.top+42),26,RED,True,"center")
        warning=("Kaikki pisteet, ratkaistut tehtävät ja lisätehtävien suoritukset "
                 "nollataan. Tehtävät 11–30 lukitaan uudelleen. Tätä toimintoa "
                 "ei voi perua.")
        draw_fitted_text(self.screen,warning,
                         pygame.Rect(panel.left+65,panel.top+110,panel.width-130,145),
                         19,14,WHITE,False,6)
        self.confirm_reset_button.draw(self.screen)
        self.cancel_reset_button.draw(self.screen)

    def draw_save_confirmation(self):
        if not self.save_confirmation_visible:
            return
        overlay=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
        overlay.fill((0,0,0,150))
        self.screen.blit(overlay,(0,0))
        panel=pygame.Rect(340,215,560,310)
        pygame.draw.rect(self.screen,"#020914",panel.move(7,8),border_radius=12)
        pygame.draw.rect(self.screen,PANEL,panel,border_radius=12)
        pygame.draw.rect(self.screen,GREEN,panel,3,border_radius=12)
        draw_text(self.screen,"PELI TALLENNETTU",(panel.centerx,panel.top+55),27,GREEN,True,"center")
        draw_fitted_text(self.screen,
                         "Pisteet, ratkaistut tehtävät ja avatut tehtäväryhmät on tallennettu. Tallennus ladataan automaattisesti seuraavalla käynnistyskerralla.",
                         pygame.Rect(panel.left+65,panel.top+115,panel.width-130,105),
                         17,13,WHITE,False,5)
        self.close_save_confirmation_button.draw(self.screen)

    def draw_quit_dialog(self):
        if not self.quit_dialog_visible:
            return
        overlay=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
        overlay.fill((0,0,0,175))
        self.screen.blit(overlay,(0,0))
        panel=pygame.Rect(270,185,700,355)
        pygame.draw.rect(self.screen,"#020914",panel.move(7,8),border_radius=12)
        pygame.draw.rect(self.screen,PANEL,panel,border_radius=12)
        pygame.draw.rect(self.screen,CYAN,panel,3,border_radius=12)
        draw_text(self.screen,"HALUATKO TALLENTAA PELIN?",
                  (panel.centerx,panel.top+65),26,CYAN,True,"center")
        draw_fitted_text(self.screen,
                         "KYLLÄ tallentaa nykyiset pisteet ja edistymisen. EI sulkee pelin ilman tallennusta.",
                         pygame.Rect(panel.left+85,panel.top+135,panel.width-170,90),
                         18,14,WHITE,False,5)
        self.quit_save_button.draw(self.screen)
        self.quit_without_save_button.draw(self.screen)

    def draw(self):
        self.screen.fill(BG)
        for button in self.information_buttons: button.draw(self.screen)
        self.progress_button.draw(self.screen)
        self.save_button.draw(self.screen)
        self.reset_button.draw(self.screen)
        draw_text(self.screen,f"PISTEET {self.score} ",(1180,45),24,YELLOW,True,"topright")
        self.task_menu_button.draw(self.screen)
        self.presentation_button.draw(self.screen)
        self.final_exam_button.enabled=self.final_exam_available()
        self.final_exam_button.draw(self.screen)
        for panel in (pygame.Rect(35,105,745,590),pygame.Rect(800,105,390,590)):
            pygame.draw.rect(self.screen,PANEL,panel); pygame.draw.rect(self.screen,PANEL_BORDER,panel,3)
        self.draw_circuit(pygame.Rect(52,125,710,540))
        draw_text(
            self.screen,
            f"TEHTÄVÄ {self.task_number}",
            (830,140),
            22,
            YELLOW,
            True
        )
        self.concept_button.draw(self.screen)
        draw_fitted_text(self.screen,self.prompt(),pygame.Rect(830,190,325,205),18,10,WHITE,True,2)
        self.input.draw(self.screen)
        draw_text(self.screen,self.challenge.answer_unit,(1134,459),23,WHITE,True,"center")
        for b in self.buttons: b.draw(self.screen)
        draw_fitted_text(self.screen,self.feedback,pygame.Rect(830,400,325,25),13,10,self.feedback_color,False)
        draw_text(self.screen,"Esc = sulje",(42,720),14,MUTED)

        # Valikko piirretään viimeisenä, jotta se aukeaa muun näkymän päälle.
        self.draw_task_menu()
        self.draw_bonus_window()
        self.draw_hint_window()
        self.draw_answer_window()
        self.draw_information_window()
        self.draw_progress_window()
        self.draw_unlock_notice()
        self.draw_final_exam()
        self.draw_presentation_dialog()
        self.draw_reset_dialog()
        self.draw_save_confirmation()
        self.draw_quit_dialog()

        # Oikea vastaus välähtää vihreänä ja väärä punaisena. Läpinäkyvä
        # kerros säilyttää piirin ja tekstin näkyvissä välähdyksen aikana.
        if self.flash and abs(self.flash)%4<2:
            overlay=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
            # GREEN ja RED ovat heksadesimaalimuotoisia merkkijonoja.
            # Muunnetaan ne ensin Pygamen Color-olioksi ja asetetaan vasta
            # sitten läpinäkyvyys. Merkkijonon purkaminen RGB-arvoiksi
            # kaatoi ohjelman välähdyksen ensimmäisellä näkyvällä ruudulla.
            color=pygame.Color(GREEN if self.flash>0 else RED)
            color.a=72
            overlay.fill(color)
            self.screen.blit(overlay,(0,0))

        self.draw_victory_animation()
        pygame.display.flip()


def run_self_test():
    pygame.init(); screen=pygame.display.set_mode((WIDTH,HEIGHT)); game=ElectricityGame(screen)
    assert len(legacy.TASK_TEMPLATE_ORDER)==30
    assert len(legacy.BONUS_QUESTIONS)==30
    assert set(HINTS)==set(range(1,31))
    assert all(symbol in NOTATION_TEXT for symbol in ("R —","Ueff —","Isc —","XL —"))
    label_adapter=PygameCanvas(screen,pygame.Rect(0,0,640,520))
    for sample in ("R1 6 Ω","C1\n2 µF","L 0.2 H","E3 12 V","3 V","9 V"):
        label_adapter.create_text(0,80,text=sample)
    assert label_adapter.drawn_texts==["R1","C1","L","E3","E1","E2"]
    for task in range(1,31):
        game.load_task(task,ignore_unlock=True)
        assert game.challenge.expected_values
        task_prompt=game.prompt()
        assert "Anna vastaus yhden desimaalin tarkkuudella." in task_prompt
        if len(game.challenge.expected_values)>1:
            assert "välilyönnit puolipisteiden jälkeen ovat vapaaehtoisia" in task_prompt
        assert "Laske" in task_prompt or "Määritä" in task_prompt
        concept_text=game.concept_information_text()
        assert "JÄNNITE- JA VIRTASUUREET" in concept_text
        template_number=legacy.TASK_TEMPLATE_ORDER[task-1]
        if template_number in legacy.ADMITTANCE_INFO_TEMPLATES:
            assert "ADMITTANSSI, KONDUKTANSSI JA SUSKEPTANSSI" in concept_text
        if game.challenge.circuit_type=="lc_oscillator":
            assert "RESONANSSITAAJUUS JA TAKAISINKYTKENTÄ" in concept_text
            assert "takaisinkytkentävastus" in concept_text.lower()
        if game.challenge.circuit_type=="ac_parallel_lc":
            assert "LC-RINNAKKAISPIIRIN RESONANSSI" in concept_text
            assert "BL + BC = 0" in concept_text
            question,choices,_correct=BONUS_QUESTION_OVERRIDES[29]
            assert "käämin ja kondensaattorin suskeptansseille" in question
            assert not any("haara-admittans" in choice.lower() or
                           "haaraimpedans" in choice.lower() for choice in choices)
        game.score=10
        game.open_hint()
        assert game.score==5 and game.hint_visible
        game.close_hint(); game.open_hint()
        assert game.score==0 and game.hint_visible
        game.close_hint(); game.open_hint()
        assert game.score==0 and not game.hint_visible
        game.score=10
        previous_challenge=game.challenge
        game.open_answer(); game.close_answer()
        assert game.challenge!=previous_challenge
        game.draw(); game.update(1/FPS)
        assert not any(re.search(
            r"[-+]?\d+(?:[.,]\d+)?\s*(?:Ω|[kmunµp]?F|[kmunµp]?H|[kmunµp]?V)",
            label,
        ) for label in game.last_circuit_texts)
    editing_field=TextInput((0,0,300,60))
    editing_field.text="4.2;4.5;8.1"
    editing_field.cursor_index=len(editing_field.text)
    editing_field.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_HOME,unicode=""))
    for _ in range(3):
        editing_field.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_DELETE,unicode=""))
    for character in "5.0":
        editing_field.handle_event(pygame.event.Event(pygame.KEYDOWN,key=ord(character),unicode=character))
    assert editing_field.text=="5.0;4.5;8.1"
    game.load_task(19,ignore_unlock=True)
    game.input.text=";".join(f"{value:.1f}" for value in game.challenge.expected_values)
    game.check_answer()
    assert game.feedback.startswith("Oikein!")
    game.load_task(19,ignore_unlock=True)
    game.input.text="; ".join(f"{value:.1f}" for value in game.challenge.expected_values)
    game.check_answer()
    assert game.feedback.startswith("Oikein!")
    game.load_task(1,ignore_unlock=True)
    game.open_concept_information(); game.draw(); game.close_information()
    game.load_task(1)
    for expected_count in (1,2):
        game.input.text=""
        game.check_answer()
        assert game.wrong_attempts==expected_count
    game.input.text=""
    game.check_answer()
    assert game.wrong_attempts==0
    assert game.input.text==""
    assert "uudet lähtöarvot" in game.feedback
    game.score=10
    old_challenge=game.challenge
    expected_answer=game.formatted_answer()
    game.open_answer()
    assert game.score==0 and game.answer_visible
    assert expected_answer.startswith("Oikea vastaus:")
    game.close_answer()
    assert not game.answer_visible and game.challenge!=old_challenge
    game.open_answer()
    assert game.score==0 and not game.answer_visible
    game.highest_score=0
    game.unlocked_through=5
    game.load_task(1)
    assert not game.load_task(11) and game.task_number==1
    game.highest_score=40; assert game.refresh_unlocks()==10
    assert game.load_task(10)
    game.highest_score=90; assert game.refresh_unlocks()==15
    game.score=0; game.refresh_unlocks()
    assert game.unlocked_through==15
    game.highest_score=170; assert game.refresh_unlocks()==26
    game.highest_score=220; assert game.refresh_unlocks()==30
    assert game.load_task(30)
    game.score=0
    game.highest_score=0
    game.scored_tasks=set()
    game.bonus_tasks=set()
    game.load_task(1,ignore_unlock=True)
    game.open_bonus()
    assert game.bonus_visible and len(game.bonus_choices)==3
    game.bonus_selected_index=game.bonus_correct_index
    game.check_bonus_answer()
    assert game.score==5 and 1 in game.bonus_tasks
    assert not game.check_bonus_button.enabled
    game.close_bonus()
    game.input.text="; ".join(f"{value:.1f}" for value in game.challenge.expected_values)
    game.check_answer()
    assert game.score==10 and 1 in game.scored_tasks
    assert not game.bonus_button.enabled
    game.load_task(2,ignore_unlock=True)
    game.score=10
    game.scored_tasks.add(2)
    game.update_bonus_button()
    assert game.bonus_button.enabled and game.bonus_button.label=="LISÄTEHTÄVÄ"
    game.open_bonus()
    game.bonus_selected_index=game.bonus_correct_index
    game.check_bonus_answer()
    assert game.score==10 and 2 in game.bonus_tasks
    assert not game.bonus_button.enabled
    game.bonus_tasks=set()
    game.score=42
    game.highest_score=90
    game.unlocked_through=20
    game.scored_tasks={1,2,3}
    game.load_task(5)
    assert game.task_progress_status(1)=="TEHTY"
    assert game.task_progress_status(5)=="TEKEMÄTTÄ"
    assert game.task_progress_status(21)=="LUKITTU"
    game.open_progress(); game.draw(); game.close_progress()
    saved_challenge=game.challenge
    game.activate_presentation()
    assert game.presentation_mode and game.score==1000
    assert game.unlocked_through==30 and game.presentation_button.label=="PELITILA"
    game.load_task(30)
    game.score=975
    game.scored_tasks.add(30)
    game.deactivate_presentation()
    assert not game.presentation_mode and game.score==42
    assert game.highest_score==90 and game.unlocked_through==15
    assert game.scored_tasks=={1,2,3} and game.task_number==5
    assert game.challenge is saved_challenge
    assert game.presentation_button.label=="ESITTELYTILA"
    assert game.task_menu_button.label=="TEHTÄVÄ 5  ▼"
    game.score=0
    game.highest_score=0
    game.unlocked_through=5
    game.scored_tasks=set()
    game.bonus_tasks=set()
    game.load_task(3)
    game.input.text="; ".join(f"{value:.1f}" for value in game.challenge.expected_values)
    game.check_answer()
    assert game.auto_advance_from==3
    game.auto_advance_at=0
    game.update(0)
    assert game.task_number==4
    assert game.task_menu_button.label=="TEHTÄVÄ 4  ▼"
    game.save_path=Path("/tmp")/f"sahkoseikkailu-self-test-{os.getpid()}.json"
    game.score=23
    game.highest_score=90
    game.unlocked_through=20
    game.scored_tasks={1,4}
    game.bonus_tasks={2}
    game.load_task(12)
    assert game.save_game() and game.save_path.exists()
    assert game.save_confirmation_visible
    game.close_save_confirmation()
    game.score=0; game.highest_score=0; game.unlocked_through=5
    game.scored_tasks=set(); game.bonus_tasks=set(); game.load_task(1)
    assert game.load_saved_game()
    assert game.score==23 and game.highest_score==90 and game.unlocked_through==20
    assert game.scored_tasks=={1,4} and game.bonus_tasks=={2} and game.task_number==12
    game.reset_game()
    assert game.score==0 and game.highest_score==0 and game.unlocked_through==5
    assert not game.scored_tasks and not game.bonus_tasks and game.task_number==1
    saved_reset=json.loads(game.save_path.read_text(encoding="utf-8"))
    assert saved_reset["score"]==0 and saved_reset["unlocked_through"]==5
    saved_before_no=game.save_path.read_text(encoding="utf-8")
    game.score=99
    game.quit_dialog_visible=True
    game.confirm_quit_without_save()
    assert not game.running
    assert game.save_path.read_text(encoding="utf-8")==saved_before_no
    game.running=True
    game.score=7
    game.highest_score=7
    game.activate_presentation()
    assert game.score==1000
    game.quit_dialog_visible=True
    game.confirm_quit_save()
    saved_on_quit=json.loads(game.save_path.read_text(encoding="utf-8"))
    assert not game.running and not game.presentation_mode
    assert saved_on_quit["score"]==7
    game.save_path.unlink(missing_ok=True)
    assert game.score_final_exam_question({0},{0})==1.0
    assert game.score_final_exam_question(set(),{0})==0.0
    assert game.score_final_exam_question({1},{0})==-0.5
    assert game.score_final_exam_question({0,1},{0,1})==1.0
    assert game.score_final_exam_question(set(),{0,1})==0.0
    pygame.quit(); print("SELF-TEST OK: kaikki 30 tehtävää ja loppukoe tarkistettiin")


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--self-test",action="store_true"); args=parser.parse_args()
    if args.self_test: run_self_test(); return
    pygame.init(); pygame.display.set_caption("Sähköseikkailu – Pygame")
    screen=pygame.display.set_mode((WIDTH,HEIGHT)); clock=pygame.time.Clock(); game=ElectricityGame(screen)
    while game.running:
        dt=clock.tick(FPS)/1000
        for event in pygame.event.get(): game.handle_event(event)
        game.update(dt); game.draw()
    pygame.quit()


if __name__=="__main__": main()
