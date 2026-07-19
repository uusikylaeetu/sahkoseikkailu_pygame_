import json
import math
import random
import copy
import sys
import types
from dataclasses import dataclass
from pathlib import Path

# Tkinter ei ole saatavilla kaikissa ympäristöissä (esim. PyInstaller-paketit
# Macilla). Luodaan kevyet nimiavaruudet, jotta moduuli latautuu normaalisti
# myös ilman _tkinter-tukea.
try:
    import tkinter as tk
    from tkinter import messagebox
except (ImportError, ModuleNotFoundError):
    tk = types.ModuleType("tkinter")
    tk.TclError = RuntimeError
    tk.Canvas = object
    tk.Frame = object
    tk.Label = object
    tk.Button = object
    tk.Entry = object
    tk.StringVar = object
    tk.IntVar = object
    tk.BooleanVar = object
    tk.Tk = object
    tk.Toplevel = object
    tk.PhotoImage = object
    tk.font = types.ModuleType("tkinter.font")
    messagebox = types.ModuleType("tkinter.messagebox")
    messagebox.showinfo = lambda *a, **k: None
    messagebox.showerror = lambda *a, **k: None
    messagebox.showwarning = lambda *a, **k: None
    messagebox.askyesno = lambda *a, **k: False
    tk.messagebox = messagebox
    sys.modules["tkinter"] = tk
    sys.modules["tkinter.messagebox"] = messagebox


WIDTH, HEIGHT = 1000, 680
MAX_TASKS = 30
# Tehtavat esitetaan lukiolaisen kannalta asteittain vaikeutuvassa jarjestyksessa.
# Arvot viittaavat alla oleviin alkuperaisiin tehtavapohjiin.
TASK_TEMPLATE_ORDER = (
    1, 2, 19, 3, 8, 4, 23, 27, 24, 5,
    20, 28, 22, 21, 25, 6, 29, 26, 7, 15,
    18, 10, 12, 13, 14, 11, 17, 16, 9, 30,
)
# Näissä tehtäväpohjissa rinnakkaisten vaihtovirtahaarojen ratkaiseminen
# perustuu admittanssien käsittelyyn.
ADMITTANCE_INFO_TEMPLATES = {9, 21, 25, 26, 29, 30}
# Tehtäväpohjat, joissa ratkaisu edellyttää solmun tunnistamista tai
# Kirchhoffin virtalain / solmujännitemenetelmän käyttämistä.
NODE_INFO_TEMPLATES = {7, 8, 10, 11, 13, 15, 16, 18}
# Thévenin-jännitettä tai portista nähtävää Thévenin-vastusta käsittelevät
# tehtäväpohjat.
THEVENIN_INFO_TEMPLATES = {10, 12, 13, 14}
# Tehtäväpohjat, joissa käytetään operaatiovahvistinta.
OPAMP_INFO_TEMPLATES = {17}
# Jännitteen ja virran peruskäsitteet ovat hyödyllisiä kaikissa tehtävissä.
ELECTRICAL_QUANTITY_INFO_TEMPLATES = set(range(1, MAX_TASKS + 1))
BG = "#071426"
PANEL = "#10233d"
CYAN = "#51e5ff"
YELLOW = "#ffd65a"
GREEN = "#65f59b"
RED = "#ff6680"
WHITE = "#f4f8ff"
MUTED = "#9bb2cc"
HINT_COST = 5
SOLUTION_COST = 10
BONUS_REWARD = 5

# Tehtäväryhmät avautuvat pistemäärän perusteella. Kun ryhmä on kerran
# avautunut, se pysyy avoinna, vaikka pisteitä käytetään myöhemmin apuihin.
TASK_CATEGORIES = (
    (1, 1, 10, 0, "Perustehtävät"),
    (2, 11, 20, 80, "Keskivaikeat tehtävät"),
    (3, 21, 26, 150, "Haastavat tehtävät"),
    (4, 27, 30, 200, "Jokeritehtävät"),
)

# Tehtäväpohjakohtaiset käsitteelliset lisäkysymykset. Kysymys ohjaa
# tarkastelemaan piiriä, mutta ei anna varsinaisen laskutehtävän numeroarvoa.
BONUS_QUESTIONS = {
    1: ("Mitkä kaksi suuretta riittävät tämän piirin virran laskemiseen?",
        ("Jännite ja resistanssi", "Teho ja taajuus", "Kapasitanssi ja induktanssi"), 0),
    2: ("Miten samansuuntaisten sarjaan kytkettyjen jännitelähteiden jännitteet yhdistetään?",
        ("Ne summataan", "Niistä otetaan keskiarvo", "Ne kerrotaan keskenään"), 0),
    3: ("Millainen rinnankytkennän kokonaisresistanssi on yksittäisten vastusten resistansseihin verrattuna?",
        ("Pienempi kuin pienimmän vastuksen resistanssi", "Suurempi kuin suurimman vastuksen resistanssi", "Yhtä suuri kuin resistanssien summa"), 0),
    4: ("Mikä suure on sama kahdessa rinnakkain kytketyssä samanlaisessa jännitelähteessä?",
        ("Jännite", "Jokaisen vastuksen virta", "Resistanssi"), 0),
    5: ("Miten ideaalisen käämin induktiivinen reaktanssi muuttuu taajuuden kasvaessa?",
        ("Se kasvaa", "Se pienenee", "Se ei muutu"), 0),
    6: ("Miten rinnakkain kytkettyjen kondensaattorien kokonaiskapasitanssi saadaan?",
        ("Kapasitanssit summataan", "Käänteisluvut summataan", "Valitaan pienin kapasitanssi"), 0),
    7: ("Mitä Kirchhoffin virtalaki ilmaisee virtapiirin solmussa?",
        ("Solmuun tulevien ja siitä lähtevien virtojen summat ovat yhtä suuret", "Kaikkien vastusten jännitteet ovat yhtä suuret", "Silmukan resistanssi on nolla"), 0),
    8: ("Mikä suure on sama kaikissa rinnakkain kytketyissä vastuksissa?",
        ("Jännite", "Virta", "Resistanssi"), 0),
    9: ("Mikä esitystapa helpottaa useiden vaihtovirtahaarojen yhdistämistä?",
        ("Kompleksisten admittanssien summaaminen", "Pelkkien resistanssien summaaminen", "Tasajännitteeksi muuttaminen"), 0),
    10: ("Kuinka suuri virta kulkee ideaalisen avoimen lähtöportin läpi?",
         ("Nolla", "Lähteen oikosulkuvirta", "Ääretön"), 0),
    11: ("Mikä on jännite ideaalisen oikosuljetun portin päiden välillä?",
         ("Nolla", "Lähdejännite", "Se riippuu vain taajuudesta"), 0),
    12: ("Miten riippumaton ideaalinen jännitelähde korvataan resistanssia määritettäessä?",
         ("Oikosululla", "Avoimella piirillä", "Kondensaattorilla"), 0),
    13: ("Milloin kaksi vastusta ovat rinnakkain?",
         ("Kun niiden molemmat päät liittyvät samoihin kahteen solmuun", "Kun niiden läpi kulkee aina eri virta", "Kun ne ovat piirroksessa vierekkäin"), 0),
    14: ("Mitä avoimesta portista katsottavaa resistanssia määritettäessä tutkitaan?",
         ("Miten vastukset yhdistyvät portin solmujen välillä", "Vain lähteen nimellisjännitettä", "Ainoastaan suurinta vastusta"), 0),
    15: ("Mikä valitaan yleensä nollapotentiaaliksi solmujännitemenetelmässä?",
         ("Yksi yhteinen vertailusolmu", "Jokainen solmu vuorollaan", "Suurimman vastuksen yläpää"), 0),
    16: ("Millä ehdolla vastussillan poikittaishaaran virta on nolla?",
         ("Poikittaishaaran päiden potentiaalit ovat samat", "Kaikki vastukset ovat erisuuria", "Lähdejännite on mahdollisimman suuri"), 0),
    17: ("Millainen kahden sarjaan kytketyn kondensaattorin yhteiskapasitanssi on?",
         ("Pienempi kuin kumpikaan kapasitanssi", "Kapasitanssien summa", "Suurempi kuin kumpikaan kapasitanssi"), 0),
    18: ("Saako Kirchhoffin yhtälöissä virran suunnan valita aluksi vapaasti?",
         ("Kyllä; negatiivinen tulos kertoo todellisen suunnan olevan vastakkainen", "Ei; väärä oletus tekee yhtälöistä ratkaisemattomat", "Vain vaihtovirtapiirissä"), 0),
    19: ("Mikä on virran ja jännitteen vaihe-ero vaihtovirtapiirissä, jossa on vain vastus?",
         ("Nolla astetta", "90 astetta", "180 astetta"), 0),
    20: ("Miten kondensaattorin kapasitiivinen reaktanssi muuttuu taajuuden kasvaessa?",
         ("Se pienenee", "Se kasvaa", "Se ei muutu"), 0),
    21: ("Mikä suure kannattaa summata rinnakkaisessa RC-piirissä?",
         ("Haarojen admittanssit", "Haarojen impedanssit suoraan", "Lähteen taajuudet"), 0),
    22: ("Milloin RLC-sarjapiirin induktiivinen ja kapasitiivinen reaktanssi kumoavat toisensa?",
         ("Kun XL = XC", "Kun R = XL + XC", "Kun taajuus on nolla"), 0),
    23: ("Mihin kondensaattorin impedanssin itseisarvo perustuu?",
         ("Kapasitiiviseen reaktanssiin", "Johtimen tasavirtavastukseen", "Induktiiviseen reaktanssiin"), 0),
    24: ("Millä kaavalla vastuksen ja käämin sarjapiirin impedanssin itseisarvo lasketaan?",
         ("|Z| = √(R² + XL²)", "|Z| = R − XL", "1/|Z| = 1/R + 1/XL"), 0),
    25: ("Mikä on sama rinnakkain kytketyn vastuksen ja käämin yli?",
         ("Jännite", "Virran vaihe", "Impedanssin itseisarvo"), 0),
    26: ("Miten RLC-rinnakkaispiirin kokonaisadmittanssi muodostetaan?",
         ("Haara-admittanssit summataan kompleksilukuina", "Haaraimpedanssit summataan suoraan", "Valitaan pienin reaktanssi"), 0),
    27: ("Miten virta vaiheistuu jännitteeseen nähden ideaalisessa käämissä?",
         ("Virta jää jännitteestä 90 astetta jälkeen", "Virta on samassa vaiheessa", "Virta johtaa jännitettä 90 astetta"), 0),
    28: ("Miten XL ja XC vaikuttavat LC-sarjapiirin kokonaisreaktanssiin?",
         ("Kokonaisreaktanssi on XL − XC", "Ne summataan aina itseisarvoina", "Niillä ei ole vaikutusta"), 0),
    29: ("Mitä tapahtuu ideaalisen LC-rinnakkaispiirin induktiivisille ja kapasitiivisille suskeptansseille resonanssissa?",
         ("Ne kumoavat toisensa", "Ne kaksinkertaistuvat", "Molemmat muuttuvat resistanssiksi"), 0),
    30: ("Mikä on turvallisin tapa pelkistää yhdistetty sarja-rinnakkaispiiri?",
         ("Aloittaa sisimmästä selvästä osapiiristä ja edetä ulospäin", "Summata kaikki komponenttiarvot", "Jättää reaktiiviset komponentit huomiotta"), 0),
}


@dataclass
class Challenge:
    voltages: tuple[int, ...]
    resistances: tuple[int, ...]
    sources_parallel: bool = False
    inductance: float = 0.0
    frequency: float = 0.0
    capacitances: tuple[float, ...] = ()
    circuit_type: str = ""
    secondary_inductance: float = 0.0
    coupling_capacitance: float = 0.0

    @staticmethod
    def solve_linear(matrix, vector):
        """Ratkaisee pienen lineaarisen yhtälöryhmän Gaussin menetelmällä."""
        rows = [list(map(float, row)) + [float(value)]
                for row, value in zip(matrix, vector)]
        size = len(rows)
        for column in range(size):
            pivot = max(range(column, size), key=lambda row: abs(rows[row][column]))
            rows[column], rows[pivot] = rows[pivot], rows[column]
            divisor = rows[column][column]
            if abs(divisor) < 1e-12:
                raise ValueError("Piirin yhtälöryhmä on singulaarinen.")
            rows[column] = [value / divisor for value in rows[column]]
            for row in range(size):
                if row == column:
                    continue
                factor = rows[row][column]
                rows[row] = [value - factor * pivot_value
                             for value, pivot_value in zip(rows[row], rows[column])]
        return tuple(row[-1] for row in rows)

    @property
    def expected_values(self):
        if self.circuit_type == "three_source_mesh":
            e1, e2, e3 = self.voltages
            r1, r2, r3, r4, r5 = self.resistances
            left_resistance = r1 + r2 + r3
            conductance = 1/left_resistance + 1/r5 + 1/r4
            node_voltage = (e1/left_resistance + e3/r5 - e2/r4) / conductance
            # Positiivinen suunta on jokaisessa haarassa yläsolmusta alasolmuun.
            return ((node_voltage-e1)/left_resistance,
                    (node_voltage-e3)/r5,
                    (node_voltage+e2)/r4)
        if self.circuit_type == "lc_oscillator":
            return (self.resonant_frequency,)
        if self.circuit_type == "nodal_voltages":
            r1, r2, r3, r4, r5 = self.resistances
            source = self.voltage
            matrix = (
                (1/r1 + 1/r2 + 1/r4, -1/r2),
                (-1/r2, 1/r2 + 1/r3 + 1/r5),
            )
            vector = (source/r1, source/r3)
            return self.solve_linear(matrix, vector)
        if self.circuit_type == "bridge_currents":
            rs, r1, r2, r3, r4, r5 = self.resistances
            source = self.voltage
            matrix = (
                (1/rs + 1/r1 + 1/r2, -1/r1, -1/r2),
                (-1/r1, 1/r1 + 1/r3 + 1/r5, -1/r5),
                (-1/r2, -1/r5, 1/r2 + 1/r4 + 1/r5),
            )
            top, left, right = self.solve_linear(matrix, (source/rs, 0, 0))
            return (
                abs((source-top)/rs), abs((top-left)/r1),
                abs((top-right)/r2), abs(left/r3),
                abs(right/r4), abs((left-right)/r5),
            )
        return (self.current,)

    @property
    def voltage(self):
        return self.voltages[0] if self.sources_parallel else sum(self.voltages)

    @property
    def resistance(self):
        if self.circuit_type == "kirchhoff":
            r1, r2, r3 = self.resistances
            return r1 + (r2 * r3) / (r2 + r3)
        return 1 / sum(1 / resistance for resistance in self.resistances)

    @property
    def inductive_reactance(self):
        return 2 * math.pi * self.frequency * self.inductance

    @property
    def capacitance(self):
        return sum(self.capacitances)

    @property
    def capacitive_reactance(self):
        if not self.capacitance:
            return 0.0
        return 1 / (2 * math.pi * self.frequency * self.capacitance)

    @property
    def resonant_frequency(self):
        """LC-oskillaattorin taajuus, kun C1 ja C2 ovat L:n kannalta sarjassa."""
        c1, c2 = self.capacitances
        equivalent_capacitance = c1 * c2 / (c1 + c2)
        return 1 / (2 * math.pi * math.sqrt(self.inductance
                                            * equivalent_capacitance))

    @property
    def impedance(self):
        if self.circuit_type.startswith("ac_"):
            return abs(self.complex_impedance)
        reactance = self.inductive_reactance or self.capacitive_reactance
        return math.hypot(self.resistance, reactance)

    @property
    def complex_impedance(self):
        """Palauttaa tehtävien 19–30 vaihtovirtapiirin kompleksisen impedanssin."""
        angular_frequency = 2 * math.pi * self.frequency

        def resistor(value):
            return complex(value, 0)

        def inductor(value):
            return 1j * angular_frequency * value

        def capacitor(value):
            return 1 / (1j * angular_frequency * value)

        def parallel(*values):
            return 1 / sum(1/value for value in values)

        kind = self.circuit_type
        if kind == "ac_resistive":
            return resistor(self.resistances[0])
        if kind == "ac_capacitive":
            return capacitor(self.capacitances[0])
        if kind == "ac_inductive":
            return inductor(self.inductance)
        if kind == "ac_series_rc":
            return resistor(self.resistances[0]) + capacitor(self.capacitances[0])
        if kind == "ac_parallel_rc":
            return parallel(resistor(self.resistances[0]),
                            capacitor(self.capacitances[0]))
        if kind == "ac_series_rl":
            return resistor(self.resistances[0]) + inductor(self.inductance)
        if kind == "ac_parallel_rl":
            return parallel(resistor(self.resistances[0]),
                            inductor(self.inductance))
        if kind == "ac_series_rlc":
            return (resistor(self.resistances[0]) + inductor(self.inductance)
                    + capacitor(self.capacitances[0]))
        if kind == "ac_parallel_rlc":
            return parallel(resistor(self.resistances[0]),
                            inductor(self.inductance),
                            capacitor(self.capacitances[0]))
        if kind == "ac_series_lc":
            return inductor(self.inductance) + capacitor(self.capacitances[0])
        if kind == "ac_parallel_lc":
            return parallel(inductor(self.inductance),
                            capacitor(self.capacitances[0]))
        if kind == "ac_complex":
            r1, r2, r3 = self.resistances
            c1, c2, c3 = self.capacitances
            inner_parallel = parallel(resistor(r2),
                                      inductor(self.secondary_inductance))
            middle = parallel(capacitor(c1), capacitor(c2) + inner_parallel)
            return (resistor(r1) + inductor(self.inductance) + middle
                    + resistor(r3) + capacitor(c3))
        raise ValueError(f"Tuntematon vaihtovirtapiiri: {kind}")

    @property
    def current(self):
        if self.circuit_type.startswith("ac_"):
            return self.voltage / abs(self.complex_impedance)
        if self.circuit_type == "three_source_mesh":
            return max(abs(value) for value in self.expected_values)
        if self.circuit_type == "lc_oscillator":
            # Vain animaation nopeusasteikkoa varten; tehtävässä kysytään taajuutta.
            return self.voltage / self.resistances[0]
        if self.circuit_type in {"nodal_voltages", "bridge_currents"}:
            return max(self.expected_values)
        if self.circuit_type.startswith("thevenin_"):
            shunt, series, branch, output = self.resistances
            if self.circuit_type == "thevenin_voltage":
                return self.voltage * branch / (series + branch)
            if self.circuit_type == "thevenin_short_current":
                parallel_load = branch * output / (branch + output)
                node_voltage = self.voltage * parallel_load / (series + parallel_load)
                return node_voltage / output
            parallel_resistance = series * branch / (series + branch)
            if self.circuit_type == "thevenin_parallel":
                return parallel_resistance
            return output + parallel_resistance
        if self.circuit_type == "coupled_lc":
            angular_frequency = 2 * math.pi * self.frequency
            c1, c2 = self.capacitances
            # L1 ja C1 muodostavat vasemman rinnakkaishaaran. Se näkyy
            # lähteelle sarjakondensaattorin Cg kautta. L2 ja C2 ovat suoraan
            # lähteen rinnalla oikeassa solmussa.
            left_admittance = 1j * (angular_frequency * c1
                                    - 1 / (angular_frequency * self.inductance))
            left_impedance = (1 / left_admittance if abs(left_admittance) > 1e-12
                              else complex(0, 1e12))
            coupling_impedance = 1 / (1j * angular_frequency
                                      * self.coupling_capacitance)
            coupling_branch = 1 / (coupling_impedance + left_impedance)
            right_admittance = 1j * (
                angular_frequency * c2
                - 1 / (angular_frequency * self.secondary_inductance)
            )
            return self.voltage * abs(right_admittance + coupling_branch)
        return self.voltage / self.impedance

    @property
    def answer_unit(self):
        if self.circuit_type == "lc_oscillator":
            return "Hz"
        if self.circuit_type == "nodal_voltages":
            return "V"
        if self.circuit_type == "thevenin_voltage":
            return "V"
        if self.circuit_type in {"thevenin_resistance", "thevenin_parallel",
                                 "thevenin_final"}:
            return "Ω"
        return "A"

    @property
    def quantity_name(self):
        if self.circuit_type == "lc_oscillator":
            return "TAAJUUS"
        if self.circuit_type == "nodal_voltages":
            return "JÄNNITTEET"
        if self.circuit_type == "bridge_currents":
            return "VIRRAT"
        if self.answer_unit == "V":
            return "JÄNNITE"
        if self.answer_unit == "Ω":
            return "VASTUS"
        return "VIRTA"


class ElectricityGame:
    def __init__(self, root):
        self.root = root
        self.root.title("Sähköseikkailu")
        self.root.resizable(False, False)
        self.canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT, bg=BG, highlightthickness=0)
        self.canvas.pack()

        self.score = 0
        self.scored_tasks = set()
        self.bonus_tasks = set()
        self.unlocked_categories = {1}
        self.streak = 0
        self.level = 1
        self.question_number = 0
        self.highest_unlocked = 0
        self.answer_locked = False
        self.wrong_attempts = 0
        self.hint_opened = False
        self.hint_dialog = None
        self.concept_info_dialog = None
        self.solution_revealed = False
        self.solution_attempt_invalidated = False
        self.solution_dialog = None
        self.bonus_dialog = None
        self.bonus_correct_index = None
        self.progress_dialog = None
        self.rules_dialog = None
        self.advice_dialog = None
        self.notation_dialog = None
        self.demo_mode = False
        self.demo_snapshot = None
        self.next_question_job = None
        self.game_completed = False
        self.completed_score_notice = None
        self.running = True
        self.phase = 0.0
        self.branch_flow = 0.0
        self.flash = 0
        self.message = "Syötä vastaus ja tarkista."
        self.message_color = MUTED
        self.challenge = Challenge((12,), (6,))
        self.answer = tk.StringVar()
        self.electrons = [i / 12 for i in range(12)]
        self.particles = []
        self.save_path = Path(__file__).with_name("sahkoseikkailu_save.json")

        self.build_ui()
        if not self.offer_saved_game():
            self.new_challenge()
            if self.completed_score_notice is not None:
                self.message = (f"Edellinen kierros suoritettu: {self.completed_score_notice} pistettä. "
                                "Uusi kierros alkoi.")
                self.message_color = GREEN
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.animate()

    def build_ui(self):
        self.canvas.create_text(55, 48, anchor="w", text="⚡ SÄHKÖSEIKKAILU", fill=WHITE,
                                font=("Arial", 25, "bold"))
        # Kaikki pääikkunan interaktiiviset kohteet ovat oikeita Tk-painikkeita.
        # Canvas varataan vain kaavion ja tekstien piirtämiseen. Tämä välttää
        # macOS:ssä havaitut Canvas-tagien ja create_window-widgetien satunnaiset
        # osuma-, kohdistus- ja grab-ongelmat.
        nav_style = {
            "font": ("Arial", 8, "bold"), "bg": "#17314f", "fg": WHITE,
            "activebackground": "#28547b", "activeforeground": WHITE,
            "relief": "flat", "cursor": "hand2", "takefocus": True,
            "borderwidth": 1, "highlightthickness": 1,
            "highlightbackground": "#4b6683",
        }
        self.rules_button = tk.Button(
            self.root, text="SÄÄNNÖT",
            command=lambda: self.show_information("rules"), **nav_style,
        )
        self.rules_button.place(x=55, y=69, width=70, height=20)
        self.advice_button = tk.Button(
            self.root, text="NEUVOJA",
            command=lambda: self.show_information("advice"), **nav_style,
        )
        self.advice_button.place(x=132, y=69, width=75, height=20)
        # TESTIPAINIKE: poista kommenttimerkit, jos 1000 pisteen LAHJA-painiketta
        # tarvitaan myöhemmin uudelleen testauksessa.
        # self.gift_button_box = self.canvas.create_rectangle(
        #     214, 69, 279, 88, fill="#17314f", outline="#4b6683", width=1,
        #     tags=("gift_action",),
        # )
        # self.gift_button_text = self.canvas.create_text(
        #     246, 78, text="LAHJA", fill=WHITE,
        #     font=("Arial", 8, "bold"), tags=("gift_action",),
        # )
        self.notation_button = tk.Button(
            self.root, text="MERKINNÄT",
            command=lambda: self.show_information("notation"), **nav_style,
        )
        self.notation_button.place(x=214, y=69, width=88, height=20)
        self.demo_button = tk.Button(
            self.root, text="ESITTELYTILA", command=self.toggle_demo_mode,
            **{**nav_style, "font": ("Arial", 7, "bold")},
        )
        self.demo_button.place(x=309, y=69, width=76, height=20)
        self.demo_status_text = self.canvas.create_text(
            945, 78, anchor="e", text="", fill=YELLOW,
            font=("Arial", 9, "bold"),
        )
        self.root.bind("<F1>", lambda _event: self.show_information("rules"))
        self.score_text = self.canvas.create_text(945, 48, anchor="e", fill=YELLOW,
                                                  font=("Arial", 16, "bold"))
        self.canvas.create_text(500, 48, anchor="w", text="TEHTÄVÄ:", fill=MUTED,
                                font=("Arial", 11, "bold"))
        primary_style = {
            "bg": "#e7eef7", "fg": "#111820", "activebackground": WHITE,
            "activeforeground": "#111820", "relief": "flat", "cursor": "hand2",
            "takefocus": True, "borderwidth": 1, "highlightthickness": 2,
            "highlightbackground": "#9aa5b1",
        }
        self.progress_button = tk.Button(
            self.root, text="EDISTYMINEN", command=self.show_progress,
            font=("Arial", 9, "bold"), **primary_style,
        )
        self.progress_button.place(x=390, y=33, width=95, height=31)
        self.root.bind("<Control-p>", lambda _event: self.show_progress())
        self.task_selector_button = tk.Button(
            self.root, text="Tehtävä 1  ▾", command=self.show_task_picker,
            font=("Arial", 11, "bold"), bg=WHITE, fg="#111820",
            activebackground="#e7eef7", activeforeground="#111820",
            relief="flat", cursor="hand2", takefocus=True, borderwidth=1,
            highlightthickness=2, highlightbackground="#9aa5b1",
        )
        self.task_selector_button.place(x=565, y=33, width=115, height=31)
        self.task_dialog = None
        self.root.bind("<Control-t>", lambda _event: self.show_task_picker())

        self.canvas.create_rectangle(45, 92, 650, 610, fill=PANEL, outline="#214567", width=2)
        self.canvas.create_rectangle(680, 92, 955, 610, fill="#0c1d34", outline="#214567", width=2)

        self.canvas.create_text(712, 130, anchor="w", text="TEHTÄVÄ", fill=CYAN,
                                font=("Arial", 13, "bold"))
        self.concept_info_button = tk.Button(
            self.root, text="LISÄTIETOA", command=self.show_concept_information,
            **nav_style,
        )
        self.task_text = self.canvas.create_text(712, 170, anchor="nw", width=210, fill=WHITE,
                                                 font=("Arial", 16, "bold"))
        self.entry = tk.Entry(self.root, textvariable=self.answer, justify="center", font=("Arial", 20, "bold"),
                              bg="#071426", fg=WHITE, insertbackground=WHITE, relief="flat")
        self.entry.place(x=712, y=361, width=150, height=48)
        self.unit_text = self.canvas.create_text(875, 409, text="A", fill=WHITE,
                                                 font=("Arial", 17, "bold"))

        self.button = tk.Button(self.root, text="KYTKE VIRTA", command=self.check_answer,
                                font=("Arial", 12, "bold"), bg=CYAN, fg="#06111f",
                                activebackground=WHITE, relief="flat", cursor="hand2")
        self.button.place(x=712, y=431, width=210, height=48)
        self.entry.bind("<Return>", lambda _event: self.check_answer())

        self.message_text = self.canvas.create_text(712, 488, anchor="nw", width=210,
                                                    fill=MUTED, font=("Arial", 10))

        self.hint_button_enabled = True
        self.solution_button_enabled = True
        self.bonus_button_enabled = True
        self.bonus_button = tk.Button(
            self.root, text=f"KYSYMYS +{BONUS_REWARD} P",
            command=self.open_bonus_question, font=("Arial", 7, "bold"),
            **primary_style,
        )
        self.bonus_button.place(x=712, y=535, width=70, height=28)
        self.hint_button = tk.Button(
            self.root, text=f"VIHJE −{HINT_COST} P", command=self.open_hint,
            font=("Arial", 7, "bold"), **primary_style,
        )
        self.hint_button.place(x=782, y=535, width=70, height=28)
        self.solution_button = tk.Button(
            self.root, text=f"VASTAUS −{SOLUTION_COST} P",
            command=self.open_solution, font=("Arial", 7, "bold"),
            **primary_style,
        )
        self.solution_button.place(x=852, y=535, width=70, height=28)

        # Oikeat painikewidgetit käyttävät samaa toimivaa command-mekanismia kuin
        # KYTKE VIRTA. macOS saa piirtää ne omalla järjestelmätyylillään.
        self.save_button = tk.Button(self.root, text="TALLENNA", command=self.save_game,
                                     font=("Arial", 9, "bold"), cursor="hand2",
                                     takefocus=True)
        self.save_button.place(x=712, y=570, width=100, height=30)
        self.restart_button = tk.Button(self.root, text="ALOITA ALUSTA",
                                        command=self.restart_game,
                                        font=("Arial", 9, "bold"), cursor="hand2",
                                        takefocus=True)
        self.restart_button.place(x=822, y=570, width=100, height=30)

        self.current_text = self.canvas.create_text(350, 145, text="", fill=CYAN,
                                                    font=("Arial", 14, "bold"))

    def _close_demo_windows(self):
        """Sulkee esittelytilan vaihtamista haittaavat apuikkunat."""
        self.close_bonus_dialog()
        self.close_hint_dialog()
        self.close_concept_information()
        self.close_solution_dialog()
        for attribute in ("task_dialog", "progress_dialog", "rules_dialog",
                          "advice_dialog", "notation_dialog"):
            window = getattr(self, attribute, None)
            if window is not None and window.winfo_exists():
                try:
                    window.grab_release()
                except tk.TclError:
                    pass
                window.destroy()
            if hasattr(self, attribute):
                setattr(self, attribute, None)

    def toggle_demo_mode(self, _event=None):
        """Avaa esittelytilan tai palauttaa sitä edeltäneen normaalin pelin."""
        if self.demo_mode:
            self.exit_demo_mode()
        else:
            self.enter_demo_mode()
        return "break"

    def enter_demo_mode(self):
        """Käynnistää tallennuksesta täysin erillisen rekrytoijaesittelyn."""
        if self.demo_mode:
            return
        if not messagebox.askyesno(
            "Avaa esittelytila",
            "Esittelytila avaa kaikki 30 tehtävää ja antaa 1000 pistettä "
            "aputoimintojen kokeilemiseen.\n\nNormaali pelitilanteesi palautuu "
            "ennalleen, kun poistut esittelytilasta. Jatketaanko?",
        ):
            return

        if self.next_question_job is not None:
            self.root.after_cancel(self.next_question_job)
            self.next_question_job = None
        self._close_demo_windows()
        self.demo_snapshot = {
            "score": self.score,
            "scored_tasks": set(self.scored_tasks),
            "bonus_tasks": set(self.bonus_tasks),
            "unlocked_categories": set(self.unlocked_categories),
            "streak": self.streak,
            "level": self.level,
            "question_number": self.question_number,
            "highest_unlocked": self.highest_unlocked,
            "challenge": copy.deepcopy(self.challenge),
            "answer": self.answer.get(),
            "answer_locked": self.answer_locked,
            "wrong_attempts": self.wrong_attempts,
            "hint_opened": self.hint_opened,
            "solution_revealed": self.solution_revealed,
            "solution_attempt_invalidated": self.solution_attempt_invalidated,
            "game_completed": self.game_completed,
            "running": self.running,
            "message": self.message,
            "message_color": self.message_color,
        }

        self.demo_mode = True
        self.score = 1000
        self.scored_tasks = set()
        self.bonus_tasks = set()
        self.unlocked_categories = {1, 2, 3, 4}
        self.highest_unlocked = MAX_TASKS
        self.streak = 0
        self.game_completed = False
        self.demo_button.configure(text="POISTU ESITTELYSTÄ",
                                   font=("Arial", 6, "bold"))
        self.canvas.itemconfigure(
            self.demo_status_text,
            text="ESITTELYTILA – EI TALLENNETA",
            fill=YELLOW,
        )
        self.save_button.configure(state="disabled")
        self.restart_button.configure(state="disabled")

        target = self.question_number if 1 <= self.question_number <= MAX_TASKS else 1
        self.open_task(target)
        self.message = ("Esittelytila: kaikki tehtävät ja aputoiminnot ovat "
                        "käytettävissä. Normaalia peliä ei muuteta.")
        self.message_color = YELLOW

    def exit_demo_mode(self):
        """Poistaa esittelytilan ja palauttaa normaalin istunnon tarkasti."""
        if not self.demo_mode or self.demo_snapshot is None:
            return
        if self.next_question_job is not None:
            self.root.after_cancel(self.next_question_job)
            self.next_question_job = None
        self._close_demo_windows()
        snapshot = self.demo_snapshot
        self.demo_snapshot = None
        self.demo_mode = False

        self.score = snapshot["score"]
        self.scored_tasks = set(snapshot["scored_tasks"])
        self.bonus_tasks = set(snapshot["bonus_tasks"])
        self.unlocked_categories = set(snapshot["unlocked_categories"])
        self.streak = snapshot["streak"]
        self.level = snapshot["level"]
        self.question_number = snapshot["question_number"]
        self.highest_unlocked = snapshot["highest_unlocked"]
        self.challenge = copy.deepcopy(snapshot["challenge"])
        self.show_challenge()

        self.wrong_attempts = snapshot["wrong_attempts"]
        self.hint_opened = snapshot["hint_opened"]
        self.solution_revealed = snapshot["solution_revealed"]
        self.solution_attempt_invalidated = snapshot["solution_attempt_invalidated"]
        self.game_completed = snapshot["game_completed"]
        self.answer_locked = snapshot["answer_locked"]
        self.running = snapshot["running"]
        self.answer.set(snapshot["answer"])
        self.message = snapshot["message"]
        self.message_color = snapshot["message_color"]

        locked = (self.answer_locked or self.solution_attempt_invalidated
                  or self.game_completed)
        self.entry.configure(state="disabled" if locked else "normal")
        self.button.configure(state="disabled" if locked else "normal")
        if self.hint_opened and not locked:
            self.configure_action_button("hint", enabled=True,
                                         text="NÄYTÄ VIHJE")
        if locked:
            self.configure_action_button("bonus", enabled=False)
            self.configure_action_button("hint", enabled=False)
            self.configure_action_button("solution", enabled=False)

        self.demo_button.configure(text="ESITTELYTILA",
                                   font=("Arial", 7, "bold"))
        self.canvas.itemconfigure(self.demo_status_text, text="")
        self.save_button.configure(state="normal")
        self.restart_button.configure(state="normal")

    def save_game(self, show_confirmation=True):
        """Tallentaa nykyisen etenemisen ja tehtävän atomisesti JSON-tiedostoon."""
        if self.demo_mode:
            if show_confirmation:
                messagebox.showinfo(
                    "Esittelytilaa ei tallenneta",
                    "Esittelytilan pisteitä ja suorituksia ei tallenneta "
                    "normaalin pelin päälle.",
                )
            return False
        data = {
            "version": 9,
            "question_number": self.question_number,
            "highest_unlocked": self.highest_unlocked,
            "score": self.score,
            "scored_tasks": sorted(self.scored_tasks),
            "bonus_tasks": sorted(self.bonus_tasks),
            "unlocked_categories": sorted(self.unlocked_categories),
            "streak": self.streak,
            "wrong_attempts": self.wrong_attempts,
            "voltages": list(self.challenge.voltages),
            "resistances": list(self.challenge.resistances),
            "sources_parallel": self.challenge.sources_parallel,
            "inductance": self.challenge.inductance,
            "frequency": self.challenge.frequency,
            "capacitances": list(self.challenge.capacitances),
            "circuit_type": self.challenge.circuit_type,
            "secondary_inductance": self.challenge.secondary_inductance,
            "coupling_capacitance": self.challenge.coupling_capacitance,
            "solution_attempt_invalidated": self.solution_attempt_invalidated,
            "completed": self.game_completed,
        }
        try:
            temporary_path = self.save_path.with_suffix(".tmp")
            temporary_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            temporary_path.replace(self.save_path)
        except OSError as error:
            messagebox.showerror("Tallennus epäonnistui", f"Peliä ei voitu tallentaa:\n{error}")
            return False
        if show_confirmation:
            self.message = f"Peli tallennettu tehtävään {self.question_number}."
            self.message_color = GREEN
        return True

    def offer_saved_game(self):
        """Tarjoaa tallennetun tehtävän jatkamista pelin käynnistyessä."""
        if not self.save_path.exists():
            return False
        try:
            data = json.loads(self.save_path.read_text(encoding="utf-8"))
            question_number = int(data["question_number"])
            voltages = tuple(int(value) for value in data["voltages"])
            resistances = tuple(int(value) for value in data["resistances"])
            if question_number < 1 or not voltages or not resistances:
                raise ValueError("Tallennuksessa on virheellisiä arvoja.")
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            messagebox.showwarning("Tallennus ei avaudu",
                                   "Tallennustiedosto on vioittunut. Uusi peli aloitetaan.")
            return False

        saved_completed = bool(data.get("completed", False))
        if saved_completed and question_number >= MAX_TASKS:
            # Valmista peliä ei voi jatkaa. Poista lopputilatallennus ja avaa
            # suoraan uusi aktiivinen kierros jäädytetyn tehtävän sijaan.
            self.completed_score_notice = int(data.get("score", 0))
            try:
                self.save_path.unlink()
            except OSError:
                pass
            return False

        next_new_task = saved_completed and question_number < MAX_TASKS
        resume_number = question_number + 1 if next_new_task else question_number
        continue_game = messagebox.askyesno(
            "Jatketaanko peliä?",
            f"Tallennettu peli jatkuu tehtävästä {resume_number}.\n\n"
            "Haluatko jatkaa siitä kohdasta?",
        )
        if not continue_game:
            try:
                self.save_path.unlink()
            except OSError:
                pass
            return False

        self.question_number = question_number
        self.highest_unlocked = max(question_number,
                                    int(data.get("highest_unlocked", question_number)))
        saved_scored_tasks = data.get("scored_tasks")
        if isinstance(saved_scored_tasks, list):
            self.scored_tasks = {
                int(number) for number in saved_scored_tasks
                if isinstance(number, int) and 1 <= number <= MAX_TASKS
            }
            self.score = int(data.get("score", 0))
            # Poista aiemman testiversion tehtävästä 1 antama 1000 pisteen
            # poikkeus myös jo olemassa olevista tallennuksista.
            saved_version = int(data.get("version", 0))
            if (saved_version <= 8 and 1 in self.scored_tasks
                    and self.score > MAX_TASKS * 10):
                self.score = max(0, self.score - 990)
            saved_bonus_tasks = data.get("bonus_tasks", [])
            self.bonus_tasks = {
                int(number) for number in saved_bonus_tasks
                if isinstance(number, int) and 1 <= number <= MAX_TASKS
            }
            saved_categories = data.get("unlocked_categories", [1])
            self.unlocked_categories = {
                int(category) for category in saved_categories
                if isinstance(category, int) and 1 <= category <= 4
            }
            self.unlocked_categories.add(1)
            # Vanhoissa tallennuksissa pysyviä avauksia ei vielä ollut.
            # Nykyinen pistemäärä saa silti avata siihen kuuluvat ryhmät.
            self.update_category_unlocks()
        else:
            # Ilman tehtäväkohtaista historiaa vanhasta tallennuksesta ei voida
            # päätellä, mitkä tehtävät on jo suoritettu tässä kierroksessa.
            self.scored_tasks = set()
            self.bonus_tasks = set()
            self.score = 0
            self.unlocked_categories = {1}
        self.streak = int(data.get("streak", 0))
        self.level = 2 if self.question_number >= 2 else 1
        if next_new_task:
            # Vanhan version viimeinen tehtävä on suoritettu, mutta uuteen
            # versioon on lisätty jatkotehtävä. Luo se uusilla lähtöarvoilla.
            self.new_challenge()
            self.message = f"Uusi tehtävä avattu: tehtävä {self.question_number}."
            self.message_color = GREEN
            return True

        self.challenge = Challenge(
            voltages, resistances,
            bool(data.get("sources_parallel", False)),
            float(data.get("inductance", 0)),
            float(data.get("frequency", 0)),
            tuple(float(value) for value in data.get("capacitances", [])),
            str(data.get("circuit_type", "")),
            float(data.get("secondary_inductance", 0)),
            float(data.get("coupling_capacitance", 0)),
        )
        self.show_challenge()
        self.wrong_attempts = max(0, min(2, int(data.get("wrong_attempts", 0))))
        saved_attempt_invalidated = bool(
            data.get("solution_attempt_invalidated", False)
        )
        if saved_attempt_invalidated:
            self.invalidate_solution_attempt()
            self.message = ("Tallennettu tehtäväkerta on lukittu, koska oikea "
                            "vastaus on avattu. Avaa tehtävä uudelleen "
                            "tehtävävalikosta saadaksesi uudet lähtöarvot.")
            self.message_color = YELLOW
        if saved_completed and question_number >= MAX_TASKS:
            self.finish_game()
        elif not saved_attempt_invalidated:
            attempt_note = (f" Virheellisiä yrityksiä: {self.wrong_attempts}/3."
                            if self.wrong_attempts else "")
            self.message = (f"Tallennettu peli ladattu: tehtävä "
                            f"{self.question_number}.{attempt_note}")
            self.message_color = GREEN
        return True

    def restart_game(self):
        """Nollaa pisteet ja aloittaa etenemisen ensimmäisestä tehtävästä."""
        if self.demo_mode:
            messagebox.showinfo(
                "Esittelytila on käytössä",
                "Poistu ensin esittelytilasta yläreunan painikkeella. "
                "Normaalia peliä ei nollattu.",
            )
            return
        if self.next_question_job is not None:
            self.root.after_cancel(self.next_question_job)
            self.next_question_job = None
        try:
            self.save_path.unlink(missing_ok=True)
        except TypeError:  # Python 3.7 -yhteensopiva varatapa.
            if self.save_path.exists():
                self.save_path.unlink()
        except OSError:
            pass
        self.score = 0
        self.scored_tasks.clear()
        self.bonus_tasks.clear()
        self.unlocked_categories = {1}
        self.streak = 0
        self.level = 1
        self.question_number = 0
        self.highest_unlocked = 0
        self.game_completed = False
        self.wrong_attempts = 0
        self.particles.clear()
        self.new_challenge()

    def on_close(self):
        """Kysyy suljettaessa, tallennetaanko nykyinen eteneminen."""
        # Estää tehtävän vaihtumisen taustalla macOS:n modaalisen ikkunan aikana.
        pending_transition = self.next_question_job is not None
        if pending_transition:
            self.root.after_cancel(self.next_question_job)
            self.next_question_job = None
        if self.demo_mode:
            close_demo = messagebox.askyesno(
                "Sulje peli",
                "Suljetaanko peli? Esittelytilan muutoksia ei tallenneta.",
            )
            if not close_demo:
                return
            self.root.destroy()
            return
        choice = messagebox.askyesnocancel(
            "Sulje peli",
            f"Tallennetaanko eteneminen tehtävään {self.question_number} ennen sulkemista?",
        )
        if choice is None:
            if pending_transition:
                self.next_question_job = self.root.after(1600, self.new_challenge)
            return
        if choice and not self.save_game(show_confirmation=False):
            return
        self.root.destroy()

    def new_challenge(self, ignore_unlock=False):
        self.next_question_job = None
        if self.question_number >= MAX_TASKS:
            if len(self.scored_tasks) == MAX_TASKS:
                self.finish_game()
            return
        target_number = self.question_number + 1
        if not ignore_unlock and not self.task_is_unlocked(target_number):
            category = self.category_for_task(target_number)
            threshold = self.category_threshold(category)
            self.message = (
                f"Seuraava tehtäväryhmä on vielä lukittu. Sen avaamiseen "
                f"tarvitaan {threshold} pistettä. Valitse tehtävävalikosta "
                "jokin avoinna oleva tehtävä."
            )
            self.message_color = YELLOW
            return
        self.question_number = target_number
        self.highest_unlocked = max(self.highest_unlocked, self.question_number)
        template_number = TASK_TEMPLATE_ORDER[self.question_number - 1]
        sources_parallel = False
        inductance, frequency = 0.0, 0.0
        capacitances = ()
        circuit_type = ""
        secondary_inductance = 0.0
        coupling_capacitance = 0.0
        if template_number == 1:
            # Ensimmäisessä tehtävässä harjoitellaan yhdellä jännitelähteellä.
            voltage, resistance = random.choice([(6, 3), (9, 3), (12, 4), (12, 6)])
            voltages = (voltage,)
            resistances = (resistance,)
        elif template_number == 2:
            # Toisessa tehtävässä lähteiden jännitteet summataan.
            source_options = [((3, 3), 3), ((3, 6), 3), ((4, 8), 4),
                              ((6, 6), 4), ((6, 12), 6), ((9, 15), 8)]
            voltages, resistance = random.choice(source_options)
            resistances = (resistance,)
        elif template_number == 3:
            # Kolmannesta tehtävästä alkaen vastukset ovat rinnan.
            parallel_options = [((3, 3), (6, 6)), ((3, 6), (6, 3)),
                                ((4, 8), (8, 8)), ((6, 6), (12, 12)),
                                ((6, 12), (12, 6)), ((9, 15), (12, 12))]
            voltages, resistances = random.choice(parallel_options)
            sources_parallel = False
        elif template_number == 4:
            # Neljännessä tehtävässä myös kaksi samanarvoista lähdettä on rinnan.
            parallel_three_options = [((6, 6), (9, 9, 9)),
                                      ((9, 9), (9, 18, 18)),
                                      ((12, 12), (12, 12, 12)),
                                      ((12, 12), (6, 12, 12)),
                                      ((18, 18), (18, 18, 18))]
            voltages, resistances = random.choice(parallel_three_options)
            sources_parallel = True
            inductance, frequency = 0.0, 0.0
        elif template_number == 5:
            # Viides tehtävä: vaihtojännitelähteen, vastuksen ja käämin sarjapiiri.
            rl_options = [((12,), (10,), 0.05, 50),
                          ((24,), (15,), 0.10, 50),
                          ((18,), (12,), 0.08, 60),
                          ((30,), (20,), 0.12, 50)]
            voltages, resistances, inductance, frequency = random.choice(rl_options)
            sources_parallel = False
        elif template_number == 6:
            # Kuudes tehtävä: sarjavastus ja kaksi rinnankytkettyä kondensaattoria.
            rc_options = [((12,), (10,), (100e-6, 100e-6), 50),
                          ((24,), (15,), (47e-6, 100e-6), 50),
                          ((18,), (12,), (68e-6, 68e-6), 60),
                          ((30,), (20,), (100e-6, 220e-6), 50)]
            voltages, resistances, capacitances, frequency = random.choice(rc_options)
        elif template_number == 7:
            # Seitsemäs tehtävä: kaksi silmukkaa Kirchhoffin lakien harjoitteluun.
            kirchhoff_options = [((12,), (4, 6, 6)),
                                 ((18,), (3, 6, 3)),
                                 ((24,), (6, 12, 12)),
                                 ((30,), (5, 10, 10))]
            voltages, resistances = random.choice(kirchhoff_options)
            circuit_type = "kirchhoff"
        elif template_number == 8:
            # Kahdeksas tehtävä: kolme rinnakkaista haaraa ja Kirchhoffin solmulaki.
            parallel_kirchhoff_options = [((12,), (6, 12, 12)),
                                          ((18,), (9, 9, 18)),
                                          ((24,), (8, 12, 24)),
                                          ((30,), (10, 15, 30))]
            voltages, resistances = random.choice(parallel_kirchhoff_options)
            circuit_type = "kirchhoff_parallel"
        elif template_number == 9:
            # Yhdeksäs tehtävä: kaksi rinnakkaista LC-piiriä, joiden ylänavat
            # on kytketty toisiinsa kondensaattorilla Cg.
            coupled_lc_options = [
                ((12,), (1,), 0.05, 0.08, (47e-6, 47e-6), 22e-6, 50),
                ((24,), (1,), 0.10, 0.15, (47e-6, 47e-6), 33e-6, 50),
                ((30,), (1,), 0.08, 0.10, (68e-6, 47e-6), 22e-6, 60),
                ((30,), (1,), 0.12, 0.08, (47e-6, 100e-6), 47e-6, 50),
            ]
            (voltages, resistances, inductance, secondary_inductance,
             capacitances, coupling_capacitance, frequency) = random.choice(
                coupled_lc_options
            )
            circuit_type = "coupled_lc"
        elif template_number <= 14:
            # Tehtävät 10–14 seuraavat saman Thévenin-muunnoksen viittä
            # kytkentäkaaviota. Ensimmäinen vastus on lähteen rinnakkaisvastus;
            # kolme muuta ovat ylähaaran sarjavastus, pystyhaara ja lähtövastus.
            thevenin_options = [
                ((10,), (20, 6, 4, 3)),
                ((12,), (24, 8, 4, 2)),
                ((18,), (30, 9, 6, 3)),
                ((24,), (40, 12, 8, 4)),
            ]
            voltages, resistances = random.choice(thevenin_options)
            thevenin_types = {
                10: "thevenin_voltage",
                11: "thevenin_short_current",
                12: "thevenin_resistance",
                13: "thevenin_parallel",
                14: "thevenin_final",
            }
            circuit_type = thevenin_types[template_number]
        elif template_number == 15:
            # Kaksi tuntematonta solmujännitettä V1 ja V2.
            nodal_options = [
                ((24,), (1, 10, 15, 40, 50)),
                ((18,), (2, 8, 12, 24, 36)),
                ((30,), (3, 12, 18, 30, 60)),
                ((12,), (1, 6, 9, 20, 30)),
            ]
            voltages, resistances = random.choice(nodal_options)
            circuit_type = "nodal_voltages"
        elif template_number == 16:
            # Wheatstonen sillan kaltainen verkko ja kuusi haaravirtaa.
            bridge_options = [
                ((30,), (6, 6, 12, 3, 3, 8)),
                ((24,), (4, 8, 12, 4, 6, 10)),
                ((18,), (3, 6, 9, 3, 6, 12)),
                ((36,), (6, 9, 18, 6, 6, 12)),
            ]
            voltages, resistances = random.choice(bridge_options)
            circuit_type = "bridge_currents"
        elif template_number == 17:
            # Operaatiovahvistimella ylläpidetty LC-oskillaattori. Käämin
            # kannalta C1 ja C2 ovat sarjassa, joten C_eq=C1*C2/(C1+C2).
            oscillator_options = [
                ((12,), (10000,), 0.010, (100e-9, 100e-9)),
                ((12,), (10000,), 0.022, (47e-9, 100e-9)),
                ((15,), (15000,), 0.047, (47e-9, 47e-9)),
                ((9,), (8200,), 0.033, (68e-9, 100e-9)),
            ]
            voltages, resistances, inductance, capacitances = random.choice(
                oscillator_options
            )
            # Taajuuskenttä merkitsee tässä, että animaatio on vaihtosuuntainen.
            frequency = 1.0
            circuit_type = "lc_oscillator"
        elif template_number == 18:
            # Kolme yhteisten ylä- ja alasolmujen välistä haaraa. Lähteiden
            # napaisuudet vastaavat mallikuvaa: E1 ja E3 aiheuttavat pudotuksen
            # ylhäältä alas kuljettaessa, E2 puolestaan jännitenousun.
            mesh_options = [
                ((30, 120, 60), (4, 5, 10, 30, 10)),
                ((24, 90, 48), (6, 6, 12, 24, 12)),
                ((18, 72, 36), (3, 6, 9, 18, 9)),
                ((36, 144, 72), (6, 9, 12, 36, 12)),
            ]
            voltages, resistances = random.choice(mesh_options)
            circuit_type = "three_source_mesh"
        else:
            # Tehtävät 19–30 käyvät mallikuvan kaksitoista vaihtovirtapiiriä
            # läpi vasemmalta oikealle ja riveittäin.
            ac_kinds = {
                19: "ac_resistive", 20: "ac_series_rc",
                21: "ac_parallel_rc", 22: "ac_series_rlc",
                23: "ac_capacitive", 24: "ac_series_rl",
                25: "ac_parallel_rl", 26: "ac_parallel_rlc",
                27: "ac_inductive", 28: "ac_series_lc",
                29: "ac_parallel_lc", 30: "ac_complex",
            }
            circuit_type = ac_kinds[template_number]
            common_options = [
                (12, 50, 10, 0.050, 100e-6),
                (24, 50, 15, 0.080, 68e-6),
                (18, 60, 12, 0.060, 47e-6),
                (30, 50, 20, 0.100, 82e-6),
            ]
            voltage, frequency, resistance, inductance, capacitance = random.choice(
                common_options
            )
            voltages = (voltage,)
            resistances = (resistance,)
            capacitances = (capacitance,)
            if circuit_type in {"ac_capacitive", "ac_inductive",
                                "ac_series_lc", "ac_parallel_lc"}:
                # Nollavastus on vain tallennusrakenteen paikanvaraaja eikä
                # kuulu näiden neljän piirin impedanssiin.
                resistances = (0,)
            if circuit_type == "ac_complex":
                complex_options = [
                    ((24,), (8, 20, 6), 0.040, 0.080,
                     (68e-6, 47e-6, 100e-6), 50),
                    ((18,), (6, 15, 9), 0.050, 0.100,
                     (47e-6, 68e-6, 82e-6), 60),
                    ((30,), (10, 30, 12), 0.080, 0.120,
                     (82e-6, 47e-6, 100e-6), 50),
                ]
                (voltages, resistances, inductance, secondary_inductance,
                 capacitances, frequency) = random.choice(complex_options)
        self.challenge = Challenge(voltages, resistances, sources_parallel,
                                   inductance, frequency, capacitances, circuit_type,
                                   secondary_inductance, coupling_capacitance)
        self.show_challenge()

    def show_challenge(self):
        """Päivittää nykyisen tehtävän tekstit uutta tai ladattua peliä varten."""
        voltages = self.challenge.voltages
        resistances = self.challenge.resistances
        self.answer.set("")
        self.close_bonus_dialog()
        self.close_hint_dialog()
        self.close_concept_information()
        self.close_solution_dialog()
        self.game_completed = False
        self.answer_locked = False
        self.wrong_attempts = 0
        self.hint_opened = False
        self.solution_revealed = False
        self.solution_attempt_invalidated = False
        self.entry.configure(state="normal")
        self.button.configure(state="normal")
        bonus_available = (self.question_number not in self.scored_tasks
                           and self.question_number not in self.bonus_tasks)
        self.configure_action_button(
            "bonus", enabled=bonus_available,
            text=(f"KYSYMYS +{BONUS_REWARD} P"
                  if bonus_available else "KYSYMYS TEHTY"),
        )
        self.configure_action_button("hint", enabled=True,
                                     text=f"VIHJE −{HINT_COST} P")
        self.configure_action_button("solution", enabled=True,
                                     text=f"VASTAUS −{SOLUTION_COST} P")
        template_number = TASK_TEMPLATE_ORDER[self.question_number - 1]
        info_templates = (ADMITTANCE_INFO_TEMPLATES | NODE_INFO_TEMPLATES
                          | THEVENIN_INFO_TEMPLATES | OPAMP_INFO_TEMPLATES
                          | ELECTRICAL_QUANTITY_INFO_TEMPLATES)
        if template_number in info_templates:
            self.concept_info_button.place(x=828, y=116, width=94, height=29)
        else:
            self.concept_info_button.place_forget()
        self.running = True
        self.message = "Syötä vastaus ja tarkista."
        self.message_color = MUTED
        if self.challenge.circuit_type.startswith("ac_"):
            kind = self.challenge.circuit_type
            names = {
                "ac_resistive": "Resistiivinen vaihtovirtapiiri",
                "ac_series_rc": "RC-sarjapiiri",
                "ac_parallel_rc": "RC-rinnakkaispiiri",
                "ac_series_rlc": "RLC-sarjapiiri",
                "ac_capacitive": "Kapasitiivinen vaihtovirtapiiri",
                "ac_series_rl": "RL-sarjapiiri",
                "ac_parallel_rl": "RL-rinnakkaispiiri",
                "ac_parallel_rlc": "RLC-rinnakkaispiiri",
                "ac_inductive": "Induktiivinen vaihtovirtapiiri",
                "ac_series_lc": "LC-sarjapiiri",
                "ac_parallel_lc": "LC-rinnakkaispiiri",
                "ac_complex": "Yhdistetty sarja–rinnakkaispiiri",
            }
            component_parts = []
            if kind == "ac_complex":
                r1, r2, r3 = resistances
                c1, c2, c3 = self.challenge.capacitances
                component_parts = [
                    f"R1={r1} Ω, R2={r2} Ω, R3={r3} Ω",
                    (f"L1={self.challenge.inductance:g} H, "
                     f"L2={self.challenge.secondary_inductance:g} H"),
                    (f"C1={c1*1e6:g} µF, C2={c2*1e6:g} µF, "
                     f"C3={c3*1e6:g} µF"),
                ]
            else:
                if kind not in {"ac_capacitive", "ac_inductive",
                                 "ac_series_lc", "ac_parallel_lc"}:
                    component_parts.append(f"R={resistances[0]} Ω")
                if kind in {"ac_series_rlc", "ac_series_rl", "ac_parallel_rl",
                            "ac_parallel_rlc", "ac_inductive", "ac_series_lc",
                            "ac_parallel_lc"}:
                    component_parts.append(f"L={self.challenge.inductance:g} H")
                if kind in {"ac_series_rc", "ac_parallel_rc", "ac_series_rlc",
                            "ac_capacitive", "ac_parallel_rlc", "ac_series_lc",
                            "ac_parallel_lc"}:
                    component_parts.append(
                        f"C={self.challenge.capacitances[0]*1e6:g} µF"
                    )
            components = ", ".join(component_parts)
            task = (f"{names[kind]}. Vaihtojännite on {voltages[0]} V ja "
                    f"taajuus {self.challenge.frequency:g} Hz. {components}.\n\n"
                    "Laske piirissä kulkevan kokonaisvirran tehollisarvo kompleksisen "
                    "impedanssin avulla.")
            source_label = (f"AC-LÄHDE   {voltages[0]} V / "
                            f"{self.challenge.frequency:g} Hz")
            resistance_label = names[kind].upper()
        elif self.challenge.circuit_type == "three_source_mesh":
            e1, e2, e3 = voltages
            r1, r2, r3, r4, r5 = resistances
            task = (f"Kolmihaaraisessa piirissä E1={e1} V, E2={e2} V ja "
                    f"E3={e3} V. Vastukset ovat R1={r1} Ω, R2={r2} Ω, "
                    f"R3={r3} Ω, R4={r4} Ω ja R5={r5} Ω.\n\n"
                    "Laske haaravirrat järjestyksessä I1; I2; I3 Kirchhoffin "
                    "lakien avulla. Positiivinen suunta on kaikissa haaroissa "
                    "yläsolmusta alasolmuun. Negatiivinen vastaus tarkoittaa "
                    "vastakkaista suuntaa.")
            source_label = f"LÄHTEET   E1 {e1} V   •   E2 {e2} V   •   E3 {e3} V"
            resistance_label = "VASTAUSJÄRJESTYS   I1; I2; I3"
        elif self.challenge.circuit_type == "lc_oscillator":
            c1, c2 = (value * 1e9 for value in self.challenge.capacitances)
            task = (f"Operaatiovahvistin ylläpitää LC-verkon värähtelyä. "
                    f"L={self.challenge.inductance * 1e3:g} mH, "
                    f"C1={c1:g} nF ja C2={c2:g} nF. "
                    f"Takaisinkytkentävastus R1={resistances[0] / 1000:g} kΩ.\n\n"
                    "Laske oskillaattorin resonanssitaajuus. Käytä käämin "
                    "kanssa vaikuttavana kapasitanssina kondensaattorien "
                    "sarjayhdistelmää.")
            source_label = "OPERAATIOVAHVISTIN • LC-OSKILLAATTORI"
            resistance_label = (f"L {self.challenge.inductance * 1e3:g} mH   •   "
                                f"C1 {c1:g} nF   •   C2 {c2:g} nF")
        elif self.challenge.circuit_type == "nodal_voltages":
            r1, r2, r3, r4, r5 = resistances
            task = (f"U={voltages[0]} V. Vastukset ovat {r1} Ω, {r2} Ω, "
                    f"{r3} Ω, {r4} Ω ja {r5} Ω.\n\n"
                    "Laske solmujännitteet V1 ja V2. Anna vastaukset "
                    "järjestyksessä V1; V2.")
            source_label = f"SOLMUJÄNNITTEET   U={voltages[0]} V"
            resistance_label = f"VASTAUSJÄRJESTYS   V1; V2"
        elif self.challenge.circuit_type == "bridge_currents":
            rs, r1, r2, r3, r4, r5 = resistances
            task = (f"U={voltages[0]} V. Siltapiirin vastukset: Rs={rs} Ω, "
                    f"R1={r1} Ω, R2={r2} Ω, R3={r3} Ω, R4={r4} Ω ja R5={r5} Ω.\n\n"
                    "Laske virtojen itseisarvot järjestyksessä "
                    "Is; I1; I2; I3; I4; I5.")
            source_label = f"SILTAPIIRI   U={voltages[0]} V"
            resistance_label = "VASTAUSJÄRJESTYS   Is; I1; I2; I3; I4; I5"
        elif self.challenge.circuit_type.startswith("thevenin_"):
            shunt, series, branch, output = resistances
            descriptions = {
                "thevenin_voltage": (
                    "Määritä avoimen lähtöportin A–B Thévenin-jännite.",
                    "ALKUPERÄINEN PIIRI"
                ),
                "thevenin_short_current": (
                    "Portti A–B oikosuljetaan. Laske oikosulkuvirta.",
                    "A–B OIKOSULJETTU"
                ),
                "thevenin_resistance": (
                    "Jännitelähde korvataan oikosululla. Laske portista A–B nähtävä vastus.",
                    "LÄHDE POISTETTU"
                ),
                "thevenin_parallel": (
                    "Laske rinnankytkettyjen sisävastusten kokonaisresistanssi.",
                    "SISÄINEN RINNANKYTKENTÄ"
                ),
                "thevenin_final": (
                    "Laske piirin Thévenin-vastus porttien A ja B väliltä.",
                    "THÉVENIN-VASTUS"
                ),
            }
            question, source_label = descriptions[self.challenge.circuit_type]
            task = (f"U={voltages[0]} V, R1={shunt} Ω, R2={series} Ω, "
                    f"R3={branch} Ω ja R4={output} Ω.\n\n{question}")
            resistance_label = (f"R1 {shunt} Ω   •   R2 {series} Ω   •   "
                                f"R3 {branch} Ω   •   R4 {output} Ω")
        elif self.challenge.circuit_type == "coupled_lc":
            c1, c2 = (value * 1e6 for value in self.challenge.capacitances)
            cg = self.challenge.coupling_capacitance * 1e6
            task = (f"Vaihtojännitelähde {voltages[0]} V / "
                    f"{self.challenge.frequency:g} Hz on kytketty oikean LC-piirin yli. "
                    f"L1={self.challenge.inductance:g} H, C1={c1:g} µF, "
                    f"L2={self.challenge.secondary_inductance:g} H, C2={c2:g} µF "
                    f"ja Cg={cg:g} µF.\n\nLaske piirissä kulkeva kokonaisvirta.")
            source_label = (f"AC-LÄHDE  {voltages[0]} V / "
                            f"{self.challenge.frequency:g} Hz")
            resistance_label = f"L1–C1   •   Cg {cg:g} µF   •   L2–C2"
        elif self.challenge.circuit_type == "kirchhoff_parallel":
            r1, r2, r3 = resistances
            task = (f"Jännitelähde {voltages[0]} V. Vastukset R1={r1} Ω, "
                    f"R2={r2} Ω ja R3={r3} Ω ovat rinnan.\n\n"
                    "Laske piirissä kulkeva kokonaisvirta Kirchhoffin solmulain avulla.")
            source_label = f"LÄHDE  {voltages[0]} V"
            resistance_label = f"R1 {r1} Ω   ‖   R2 {r2} Ω   ‖   R3 {r3} Ω"
        elif self.challenge.circuit_type == "kirchhoff":
            r1, r2, r3 = resistances
            task = (f"Jännitelähde {voltages[0]} V. Vastukset R1={r1} Ω, "
                    f"R2={r2} Ω ja R3={r3} Ω.\n\n"
                    "Laske piirissä kulkeva kokonaisvirta Kirchhoffin lakien avulla.")
            source_label = f"LÄHDE  {voltages[0]} V"
            resistance_label = f"R1 {r1} Ω   •   R2 {r2} Ω   •   R3 {r3} Ω"
        elif self.challenge.capacitances:
            c1, c2 = (capacitance * 1e6 for capacitance in self.challenge.capacitances)
            task = (f"Vaihtojännite {voltages[0]} V, vastus {resistances[0]} Ω, "
                    f"kondensaattorit {c1:g} µF ja {c2:g} µF rinnan sekä taajuus "
                    f"{self.challenge.frequency:g} Hz.\n\n"
                    "Laske piirissä kulkeva virta.")
            source_label = f"AC-LÄHDE  {voltages[0]} V / {self.challenge.frequency:g} Hz"
            resistance_label = f"R {resistances[0]} Ω   •   C {c1:g} µF ‖ {c2:g} µF"
        elif self.challenge.inductance:
            task = (f"Vaihtojännite {voltages[0]} V, vastus {resistances[0]} Ω, "
                    f"käämi {self.challenge.inductance:g} H ja taajuus "
                    f"{self.challenge.frequency:g} Hz.\n\n"
                    "Laske piirissä kulkeva virta.")
            source_label = f"AC-LÄHDE  {voltages[0]} V / {self.challenge.frequency:g} Hz"
            resistance_label = (f"R {resistances[0]} Ω   •   "
                                f"L {self.challenge.inductance:g} H")
        elif len(voltages) == 1:
            task = (f"Jännite on {voltages[0]} V ja vastus {resistances[0]} Ω.\n\n"
                    "Laske piirissä kulkeva virta.")
            source_label = f"PARISTO  {voltages[0]} V"
            resistance_label = f"VASTUS  {resistances[0]} Ω"
        elif len(resistances) == 1:
            resistance = resistances[0]
            task = (f"Sarjassa on kaksi lähdettä: {voltages[0]} V ja {voltages[1]} V. "
                    f"Vastus on {resistance} Ω.\n\n"
                    "Laske piirissä kulkeva virta.")
            source_label = f"LÄHTEET  {voltages[0]} V + {voltages[1]} V"
            resistance_label = f"VASTUS  {resistance} Ω"
        elif len(resistances) == 2:
            r1, r2 = resistances
            task = (f"Kaksi lähdettä: {voltages[0]} V ja {voltages[1]} V. "
                    f"Vastukset {r1} Ω ja {r2} Ω ovat rinnan.\n\n"
                    "Laske piirissä kulkeva kokonaisvirta.")
            source_label = f"LÄHTEET  {voltages[0]} V + {voltages[1]} V"
            resistance_label = f"RINNAN  {r1} Ω ‖ {r2} Ω"
        else:
            r1, r2, r3 = resistances
            task = (f"Kaksi {voltages[0]} V lähdettä on rinnan. Vastukset "
                    f"{r1} Ω, {r2} Ω ja {r3} Ω ovat rinnan.\n\n"
                    "Laske piirissä kulkeva kokonaisvirta.")
            source_label = f"RINNAN  {voltages[0]} V ‖ {voltages[1]} V"
            resistance_label = f"RINNAN  {r1} Ω ‖ {r2} Ω ‖ {r3} Ω"
        task += "\n\nAnna vastaus yhden desimaalin tarkkuudella."
        self.canvas.itemconfigure(self.task_text, text=task)
        self.canvas.itemconfigure(self.task_text,
                                  font=("Arial", 12, "bold"))
        unit = self.challenge.answer_unit
        multiple_answers = len(self.challenge.expected_values) > 1
        self.entry.place_configure(width=190 if multiple_answers else 150)
        self.canvas.coords(self.unit_text, 915 if multiple_answers else 875, 409)
        self.canvas.itemconfigure(self.unit_text, text=unit)
        # Tehtäväteksti ja vastauskentän yksikkö kertovat jo kysytyn suureen.
        # Kaavioalueelle ei lisätä erillistä "VIRTA ? A" -tyyppistä otsikkoa.
        self.canvas.itemconfigure(self.current_text, text="")
        self.button.configure(text=("KYTKE VIRTA" if unit == "A"
                                    else "TARKISTA VASTAUS"))
        self.update_task_menu()
        self.task_selector_button.configure(
            text=f"Tehtävä {self.question_number}  ▾")
        self.entry.focus_set()

    def task_selector_clicked(self, _event=None):
        """Varmistaa hiiren painalluksen käsittelyn macOS:llä."""
        self.show_task_picker()
        return "break"

    @staticmethod
    def category_for_task(number):
        """Palauttaa tehtävän ryhmän numeron 1–4."""
        for category, first, last, _threshold, _name in TASK_CATEGORIES:
            if first <= number <= last:
                return category
        return 1

    @staticmethod
    def category_threshold(category):
        """Palauttaa ryhmän pysyvään avaamiseen vaaditun pistemäärän."""
        for number, _first, _last, threshold, _name in TASK_CATEGORIES:
            if number == category:
                return threshold
        return 0

    @staticmethod
    def category_name(category):
        """Palauttaa tehtäväryhmän käyttäjälle näytettävän nimen."""
        for number, _first, _last, _threshold, name in TASK_CATEGORIES:
            if number == category:
                return name
        return "Tehtävät"

    def task_is_unlocked(self, number):
        """Kertoo, kuuluuko tehtävä jo pysyvästi avattuun ryhmään."""
        if self.demo_mode:
            return 1 <= number <= MAX_TASKS
        return self.category_for_task(number) in self.unlocked_categories

    def update_category_unlocks(self):
        """Avaa saavutetut ryhmät pysyvästi ja palauttaa niiden nimet."""
        newly_unlocked = []
        for category, _first, _last, threshold, name in TASK_CATEGORIES:
            if category not in self.unlocked_categories and self.score >= threshold:
                self.unlocked_categories.add(category)
                newly_unlocked.append(name)
        return newly_unlocked

    def show_task_picker(self):
        """Avaa varmatoimisen erillisen ikkunan tehtävän valitsemiseksi."""
        if self.task_dialog is not None and self.task_dialog.winfo_exists():
            self.task_dialog.deiconify()
            self.task_dialog.lift()
            self.task_dialog.focus_force()
            return

        dialog = tk.Toplevel(self.root)
        self.task_dialog = dialog
        dialog.title("Valitse tehtävä")
        dialog.configure(bg=BG)
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.protocol("WM_DELETE_WINDOW", self.close_task_picker)

        tk.Label(dialog, text="VALITSE TEHTÄVÄ", bg=BG, fg=WHITE,
                 font=("Arial", 15, "bold")).grid(
                     row=0, column=0, columnspan=4, padx=18, pady=(18, 12)
                 )
        for index, number in enumerate(range(1, MAX_TASKS + 1)):
            row, column = divmod(index, 4)
            unlocked = self.task_is_unlocked(number)
            button = tk.Button(
                dialog, text=(f"Tehtävä {number}" if unlocked
                              else f"Tehtävä {number}  🔒"),
                command=lambda task_number=number: self.choose_task(task_number),
                font=("Arial", 11, "bold"), cursor="hand2", width=10,
                takefocus=True,
                state="normal" if unlocked else "disabled",
            )
            button.grid(row=row+1, column=column, padx=6, pady=6)

        close_button = tk.Button(dialog, text="SULJE", command=self.close_task_picker,
                                 font=("Arial", 10, "bold"), cursor="hand2")
        close_row = math.ceil(MAX_TASKS / 4) + 1
        close_button.grid(row=close_row, column=0, columnspan=4,
                          pady=(12, 18), ipadx=24)

        self.root.update_idletasks()
        dialog.update_idletasks()
        x = self.root.winfo_rootx() + (self.root.winfo_width()-dialog.winfo_width())//2
        y = self.root.winfo_rooty() + 70
        dialog.geometry(f"+{max(0, x)}+{max(0, y)}")
        dialog.lift()
        dialog.focus_force()
        # Valitsin ei lukitse pääikkunaa. macOS:ssa modal grab saattoi jäädä
        # voimaan ikkunan vaihtuessa ja tehdä muut painikkeet näennäisesti
        # kuolleiksi.

    def close_task_picker(self):
        """Sulkee tehtävän valintaikkunan turvallisesti."""
        if self.task_dialog is not None and self.task_dialog.winfo_exists():
            self.task_dialog.destroy()
        self.task_dialog = None
        if self.root.winfo_exists():
            self.root.focus_force()

    def choose_task(self, number):
        """Sulkee valintaikkunan ja avaa valitun tehtävän."""
        self.close_task_picker()
        self.open_task(number)

    def progress_action_clicked(self, _event=None):
        """Avaa tehtäväkohtaisen edistymisnäkymän koko osuma-alueelta."""
        self.show_progress()
        return "break"

    def claim_test_gift(self, _event=None):
        """Lisää testaamista varten 1000 pistettä ja avaa pisterajat."""
        self.score += 1000
        newly_unlocked = self.update_category_unlocks()
        self.message = "Lahja avattu: +1000 pistettä."
        if newly_unlocked:
            self.message += (" Avautuivat: "
                             + ", ".join(newly_unlocked) + ".")
        self.message_color = GREEN
        self.flash = 12
        return "break"

    def show_progress(self):
        """Näyttää ratkaistut ja ratkaisemattomat tehtävät erillisessä ikkunassa."""
        if self.progress_dialog is not None and self.progress_dialog.winfo_exists():
            self.progress_dialog.deiconify()
            self.progress_dialog.lift()
            self.progress_dialog.focus_force()
            return

        dialog = tk.Toplevel(self.root)
        self.progress_dialog = dialog
        dialog.title("Edistyminen")
        dialog.configure(bg=BG)
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.protocol("WM_DELETE_WINDOW", self.close_progress)

        completed_count = len(self.scored_tasks)
        tk.Label(dialog, text="EDISTYMINEN", bg=BG, fg=CYAN,
                 font=("Arial", 16, "bold")).grid(
                     row=0, column=0, columnspan=2, padx=24, pady=(20, 6)
                 )
        tk.Label(dialog,
                 text=f"Ratkaistu {completed_count}/{MAX_TASKS} tehtävää",
                 bg=BG, fg=WHITE, font=("Arial", 11, "bold")).grid(
                     row=1, column=0, columnspan=2, pady=(0, 14)
                 )

        rows_per_column = math.ceil(MAX_TASKS / 2)
        for index, number in enumerate(range(1, MAX_TASKS + 1)):
            row = index % rows_per_column + 2
            column = index // rows_per_column
            solved = number in self.scored_tasks
            unlocked = self.task_is_unlocked(number)
            if solved:
                status = "RATKAISTU"
                foreground = GREEN
            elif unlocked:
                status = "RATKAISEMATTA"
                foreground = MUTED
            else:
                status = "LUKITTU"
                foreground = YELLOW
            background = "#17314f" if number == self.question_number else BG
            tk.Label(
                dialog, text=f"Tehtävä {number:2d}  —  {status}",
                anchor="w", width=25, bg=background, fg=foreground,
                font=("Arial", 10, "bold" if solved else "normal"),
                padx=8, pady=3,
            ).grid(row=row, column=column, padx=8, pady=1, sticky="ew")

        close_row = rows_per_column + 2
        tk.Button(dialog, text="SULJE", command=self.close_progress,
                  font=("Arial", 10, "bold"), cursor="hand2",
                  takefocus=True).grid(
                      row=close_row, column=0, columnspan=2,
                      pady=(16, 20), ipadx=28
                  )

        self.root.update_idletasks()
        dialog.update_idletasks()
        x = self.root.winfo_rootx() + (
            self.root.winfo_width() - dialog.winfo_width()
        ) // 2
        y = self.root.winfo_rooty() + 55
        dialog.geometry(f"+{max(0, x)}+{max(0, y)}")
        dialog.lift()
        dialog.focus_force()
        # Edistymisikkuna on tarkoituksella ei-modaalinen.

    def close_progress(self):
        """Sulkee edistymisikkunan turvallisesti."""
        if (self.progress_dialog is not None
                and self.progress_dialog.winfo_exists()):
            self.progress_dialog.destroy()
        self.progress_dialog = None
        if self.root.winfo_exists():
            self.root.focus_force()

    def update_task_menu(self):
        """Säilytetty kutsupaikkaa varten; valintaikkuna luodaan avattaessa."""

    def show_information(self, kind):
        """Avaa pysyvän sääntö- tai neuvontaikkunan pääpelin rinnalle."""
        if kind == "rules":
            attribute = "rules_dialog"
            title = "Pelin säännöt"
            heading = "SÄÄNNÖT"
            body = (
                "PELIN TAVOITE\n"
                "Pelin läpäiseminen edellyttää, että ratkaiset kaikki 30 tehtävää.\n\n"
                "PISTEET\n"
                "- Jokaisen tehtävän ensimmäisestä oikeasta suorituksesta "
                "saa 10 pistettä.\n"
                "- Väärä vastaus ei vähennä pisteitä.\n"
                "- Kolmen väärän vastauksen jälkeen tehtävään arvotaan "
                "uudet lähtöarvot.\n"
                "- Samasta tehtävästä saa pisteet vain kerran.\n\n"
                "LISÄKYSYMYS, VIHJE JA VASTAUS\n"
                "- Lisäkysymyksen oikeasta vastauksesta saa 5 pistettä. "
                "Tällöin tavallisen tehtävän jäljelle jäävä palkkio on 5 "
                "pistettä, joten lisäkysymykseen vastaaminen ei kasvata tehtävän "
                "kokonaispalkkiota.\n"
                "- Vihje maksaa 5 pistettä.\n"
                "- Valmiin numeroarvon näyttäminen maksaa 10 pistettä. Kun "
                "oikea vastaus suljetaan, tehtävään arvotaan uudet lähtöarvot.\n"
                "- Vihjettä tai valmista vastausta ei voi avata, jos pisteet eivät riitä.\n\n"
                "ETENEMINEN\n"
                "- Perustehtävät 1–10 ovat avoinna heti.\n"
                "- Keskivaikeat tehtävät 11–20 avautuvat 80 pisteellä.\n"
                "- Haastavat tehtävät 21–26 avautuvat 150 pisteellä.\n"
                "- Jokeritehtävät 27–30 avautuvat 200 pisteellä.\n"
                "- Kerran avattu tehtäväryhmä pysyy avoinna, vaikka pisteitä "
                "käytettäisiin myöhemmin.\n\n"
                "EDISTYMINEN näyttää ratkaistut tehtävät. TALLENNA säilyttää "
                "tilanteen ja avatut tehtävät. ALOITA ALUSTA nollaa pisteet ja "
                "suoritukset."
            )
        elif kind == "advice":
            attribute = "advice_dialog"
            title = "Neuvoja pelaamiseen"
            heading = "NEUVOJA"
            body = (
                "- Ratkaise helpot tehtävät mahdollisuuksien mukaan "
                "ilman apua. Näin säästät pisteitä vaikeampiin "
                "tehtäviin ja avaat seuraavat tehtäväryhmät nopeammin.\n\n"
                "- Väärästä vastauksesta ei menetä pisteitä. Tarkista siis "
                "laskusi rauhassa ja uskalla yrittää ennen vihjeen avaamista. "
                "Kolmas väärä vastaus vaihtaa lähtöarvot, joten oikeaa "
                "vastausta ei kannata yrittää arvata.\n\n"
                "- Jos olet tehtävien kanssa jumissa tai pisteet ovat vähissä, aloita "
                "tehtäväkohtaisesta lisäkysymyksestä. Se kertaa tarvittavaa "
                "käsitettä ja antaa oikeasta vastauksesta 5 pistettä.\n\n"
                "- Käytä seuraavaksi vihjettä. Se ohjaa oikeaan lakiin tai "
                "laskutapaan, mutta jättää varsinaisen ratkaisun sinulle.\n\n"
                "- Avaa valmis vastaus vasta viimeisenä keinona. Se maksaa "
                "enemmän pisteitä ja pakottaa ratkaisemaan tehtävän uusilla "
                "lähtöarvoilla.\n\n"
                "- Jos vaikea tehtävä ei aukea, palaa aiempiin saman aiheen "
                "tehtäviin. Tavoitteena ei ole kerätä mahdollisimman suurta "
                "pistemäärää, vaan oppia ratkaisemaan kaikki tehtävätyypit.\n\n"
                "- Anna numeeriset vastaukset yhden desimaalin tarkkuudella. \n\n"
                "- Usean vastauksen tehtävissä erota arvot puolipisteillä. \n\n"
                "- Tekoälyn käyttö ei ole suositeltavaa. Se on oikotie tehtävän ratkaisuun, mutta ei asioiden oppimiseen."
            )
        else:
            attribute = "notation_dialog"
            title = "Sähköopin merkinnät"
            heading = "MERKINNÄT"
            body = (
                "R — resistanssi, yksikkö ohmi (Ω)\n\n"
                "L — induktanssi, yksikkö henry (H)\n\n"
                "C — kapasitanssi, yksikkö faradi (F)\n\n"
                "Z — impedanssi eli vaihtovirran kulkua vastustava suure, "
                "yksikkö ohmi (Ω)\n\n"
                "Y — admittanssi eli impedanssin käänteisluku, yksikkö "
                "siemens (S)\n\n"
                "G — konduktanssi eli admittanssin reaaliosa. Puhtaalle "
                "vastukselle G = 1/R, yksikkö siemens (S)\n\n"
                "B — suskeptanssi eli admittanssin imaginääriosa, joka "
                "kuvaa käämien ja kondensaattorien vaikutusta vaihtovirran "
                "kulkuun, yksikkö siemens (S)\n\n"
                "U — jännite eli kahden pisteen välinen potentiaaliero, "
                "yksikkö voltti (V)\n\n"
                "Ueff — jännitteen tehollisarvo. Sinimuotoiselle "
                "jännitteelle Ueff = Umax/√2, yksikkö voltti (V)\n\n"
                "Umax — sinimuotoisen jännitteen huippuarvo eli "
                "hetkellisen jännitteen suurin itseisarvo, yksikkö voltti (V)\n\n"
                "Ieff — virran tehollisarvo. Sinimuotoiselle virralle "
                "Ieff = Imax/√2, yksikkö ampeeri (A)\n\n"
                "Imax — sinimuotoisen virran huippuarvo eli hetkellisen "
                "virran suurin itseisarvo, yksikkö ampeeri (A)\n\n"
                "RTh — Thévenin-vastus eli portista nähtävä piirin "
                "sisäinen vastus, yksikkö ohmi (Ω)\n\n"
                "UTh — Thévenin-jännite eli avoimen lähtöportin jännite, "
                "yksikkö voltti (V)\n\n"
                "Isc — oikosulkuvirta eli oikosuljetun portin läpi kulkeva "
                "virta, yksikkö ampeeri (A)\n\n"
                "Rkok — piirin tai vastusryhmän kokonaisresistanssi, "
                "yksikkö ohmi (Ω)\n\n"
                "XC — kapasitiivinen reaktanssi, yksikkö ohmi (Ω)\n\n"
                "XL — induktiivinen reaktanssi, yksikkö ohmi (Ω)\n\n"
                "f — taajuus, yksikkö hertsi (Hz)"
            )

        existing = getattr(self, attribute)
        if existing is not None and existing.winfo_exists():
            existing.deiconify()
            existing.lift()
            existing.focus_force()
            return

        dialog = tk.Toplevel(self.root)
        setattr(self, attribute, dialog)
        dialog.title(title)
        dialog.configure(bg=BG)
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.protocol("WM_DELETE_WINDOW",
                        lambda dialog_kind=kind: self.close_information(dialog_kind))

        tk.Label(dialog, text=heading, bg=BG, fg=CYAN,
                 font=("Arial", 16, "bold")).pack(
                     padx=30, pady=(22, 14)
                 )
        if kind == "notation":
            text_frame = tk.Frame(dialog, bg=BG)
            text_frame.pack(padx=30, pady=(0, 18), fill="both", expand=True)
            notation_text = tk.Text(
                text_frame, width=62, height=25, wrap="word",
                bg=BG, fg=WHITE, font=("Arial", 11), relief="flat",
                borderwidth=0, highlightthickness=0, cursor="arrow",
            )
            scrollbar = tk.Scrollbar(text_frame, command=notation_text.yview)
            notation_text.configure(yscrollcommand=scrollbar.set)
            notation_text.insert("1.0", body)
            notation_text.configure(state="disabled")
            notation_text.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
        else:
            tk.Label(dialog, text=body, wraplength=560, justify="left",
                     anchor="w", bg=BG, fg=WHITE,
                     font=("Arial", 11)).pack(
                         padx=30, pady=(0, 18), anchor="w"
                     )
        tk.Button(
            dialog, text="SULJE",
            command=lambda dialog_kind=kind: self.close_information(dialog_kind),
            font=("Arial", 10, "bold"), cursor="hand2", takefocus=True,
        ).pack(pady=(0, 22), ipadx=26)

        self.root.update_idletasks()
        dialog.update_idletasks()
        x = self.root.winfo_rootx() + (
            self.root.winfo_width() - dialog.winfo_width()
        ) // 2
        y = self.root.winfo_rooty() + 55
        dialog.geometry(f"+{max(0, x)}+{max(0, y)}")
        dialog.lift()
        dialog.focus_force()

    def close_information(self, kind):
        """Sulkee sääntö-, neuvonta- tai merkintäikkunan turvallisesti."""
        attributes = {
            "rules": "rules_dialog",
            "advice": "advice_dialog",
            "notation": "notation_dialog",
        }
        attribute = attributes[kind]
        dialog = getattr(self, attribute)
        if dialog is not None and dialog.winfo_exists():
            dialog.destroy()
        setattr(self, attribute, None)

    def bonus_action_clicked(self, _event=None):
        """Canvas-painikkeen luotettava klikkauskäsittelijä."""
        if self.bonus_button_enabled:
            self.open_bonus_question()
        return "break"

    def hint_action_clicked(self, _event=None):
        """Canvas-painikkeen luotettava klikkauskäsittelijä."""
        if self.hint_button_enabled:
            self.open_hint()
        return "break"

    def solution_action_clicked(self, _event=None):
        """Canvas-painikkeen luotettava klikkauskäsittelijä."""
        if self.solution_button_enabled:
            self.open_solution()
        return "break"

    def configure_action_button(self, kind, enabled=None, text=None):
        """Päivittää oikean Tk-toimintopainikkeen tekstin ja tilan."""
        if kind == "bonus":
            button = self.bonus_button
            if enabled is not None:
                self.bonus_button_enabled = enabled
            active = self.bonus_button_enabled
        elif kind == "hint":
            button = self.hint_button
            if enabled is not None:
                self.hint_button_enabled = enabled
            active = self.hint_button_enabled
        else:
            button = self.solution_button
            if enabled is not None:
                self.solution_button_enabled = enabled
            active = self.solution_button_enabled
        options = {
            "state": "normal" if active else "disabled",
            "bg": "#e7eef7" if active else "#65717f",
            "fg": "#111820" if active else "#c5ccd4",
            "disabledforeground": "#c5ccd4",
        }
        if text is not None:
            options["text"] = text
        button.configure(**options)

    def set_action_hover(self, kind, hovering):
        """Säilytetty yhteensopivuutta varten; Tk-painike hoitaa hoverin itse."""

    def hint_for_current_task(self):
        """Palauttaa tehtäväkohtaisen ohjaavan vihjeen paljastamatta vastausta."""
        hints = {
            1: "Ohmin laki yhdistää jännitteen, virran ja resistanssin: U = RI.",
            2: "Sarjaan kytkettyjen samansuuntaisten lähteiden jännitteet summataan.",
            3: ("Tässä vaihtovirtapiirissä on vain vastus. Siksi "
                "impedanssi on yhtä suuri kuin resistanssi: Z = R."),
            4: ("Laske ensin rinnakkain kytkettyjen vastusten "
                "kokonaisresistanssi: 1/Rkok = 1/R1 + 1/R2."),
            5: ("Rinnakkain kytkettyjen vastusten yli on sama jännite. "
                "Laske jokaisen vastuksen virta kaavalla I = U/R ja "
                "summaa virrat."),
            6: ("Kaksi samanlaista rinnakkain kytkettyä jännitelähdettä "
                "tuottaa saman jännitteen kuin yksi lähde."),
            7: ("Kondensaattorin reaktanssi on XC = 1/(2πfC). "
                "Kun piirissä on vain kondensaattori, impedanssin "
                "itseisarvo on |Z| = XC."),
            8: ("Käämin reaktanssi on XL = 2πfL. Kun piirissä on vain "
                "käämi, impedanssin itseisarvo on |Z| = XL."),
            9: ("Laske ensin käämin reaktanssi XL = 2πfL. Vastuksen ja "
                "käämin sarjapiirissä impedanssin itseisarvo on "
                "|Z| = √(R² + XL²)."),
            10: ("Laske ensin käämin reaktanssi XL = 2πfL. Vastuksen ja "
                 "käämin sarjapiirin impedanssin itseisarvo on "
                 "|Z| = √(R² + XL²)."),
            11: ("Laske ensin kondensaattorin reaktanssi "
                 "XC = 1/(2πfC). Vastuksen ja kondensaattorin "
                 "sarjapiirissä |Z| = √(R² + XC²)."),
            12: ("Käämin ja kondensaattorin vaikutukset vähentävät toisiaan, joten "
                 "sarjapiirin impedanssin itseisarvo on |XL − XC|."),
            13: ("Käämi ja kondensaattori siirtävät virran vaihetta "
                 "vastakkaisiin suuntiin, joten kokonaisreaktanssi on "
                 "X = XL − XC."),
            14: "Rinnakkaispiirissä on usein helpointa summata haarojen kompleksiset admittanssit.",
            15: ("Laske R- ja L-haarojen admittanssit erikseen ja summaa ne "
                 "kokonaisadmittanssiksi Y. Piirin kokonaisimpedanssi on "
                 "kokonaisadmittanssin käänteisluku: Z = 1/Y."),
            16: ("Rinnakkain kytkettyjen kondensaattorien kapasitanssit "
                 "summataan. Kondensaattorin reaktanssi pienenee taajuuden "
                 "kasvaessa."),
            17: ("LC-rinnakkaispiirin kokonaisadmittanssi saadaan laskemalla "
                 "käämin ja kondensaattorin admittanssit yhteen."),
            18: "RLC-rinnakkaispiirissä kokonaisadmittanssi on YR + YL + YC.",
            19: ("Sovella solmuun Kirchhoffin virtalakia ja kumpaankin "
                 "silmukkaan Kirchhoffin jännitelakia."),
            20: ("Kirjoita solmuille V1 ja V2 Kirchhoffin virtalain "
                 "mukaiset yhtälöt."),
            21: ("Merkitse ylä- ja alasolmun jännite-ero V:ksi. Kirjoita "
                 "kunkin vastuksen virta V:n avulla ja käytä ΣI = 0."),
            22: "Avoimessa lähtöportissa lähtöhaaran virta on nolla. Etsi portin solmujännite.",
            23: "Riippumaton ideaalinen jännitelähde deaktivoidaan korvaamalla se oikosululla.",
            24: "Kun kaksi vastusta on samojen solmujen välissä, niiden käänteiset resistanssit summataan.",
            25: "Tarkista, mikä vastus on portin kanssa sarjassa ja mitkä sisävastukset ovat rinnan.",
            26: ("Oikosuljetun portin päiden välinen jännite on nolla. "
                 "Selvitä ensin sitä syöttävän solmun jännite."),
            27: "Käämin näkemä C1:n ja C2:n kapasitanssi on niiden sarjakapasitanssi. Käytä LC-resonanssiehtoa.",
            28: ("Merkitse R1:n, R3:n ja R5:n yhteisen liitospisteen sekä "
                 "R2:n, R4:n ja R5:n yhteisen liitospisteen jännitteet "
                 "tuntemattomiksi. Muodosta kummallekin liitospisteelle "
                 "Kirchhoffin virtalain mukainen yhtälö."),
            29: "Muodosta kummankin LC-haaran kompleksinen admittanssi ja käsittele Cg niiden välisenä impedanssina.",
            30: ("Aloita laskemalla R2:n ja L2:n rinnankytkennän "
                 "impedanssi. Tämä yhdistelmä on sarjassa C2:n kanssa, "
                 "ja niiden yhteisimpedanssi on rinnan C1:n kanssa. Lisää "
                 "lopuksi piirin sarjassa olevien muiden komponenttien "
                 "impedanssit."),
        }
        return hints[self.question_number]

    def open_bonus_question(self):
        """Avaa nykyiseen tehtävään liittyvän viiden pisteen käsitekysymyksen."""
        if (self.game_completed or self.answer_locked
                or self.question_number in self.scored_tasks
                or self.question_number in self.bonus_tasks):
            return
        if self.bonus_dialog is not None and self.bonus_dialog.winfo_exists():
            self.bonus_dialog.deiconify()
            self.bonus_dialog.lift()
            self.bonus_dialog.focus_force()
            return

        template_number = TASK_TEMPLATE_ORDER[self.question_number - 1]
        question, choices, correct_index = BONUS_QUESTIONS[template_number]
        # Säilytä tieto oikeasta vaihtoehdosta, mutta arvo näkyvä järjestys
        # uudelleen jokaisella kysymyksen avauskerralla.
        shuffled_choices = list(enumerate(choices))
        random.shuffle(shuffled_choices)
        self.bonus_correct_index = next(
            displayed_index
            for displayed_index, (original_index, _choice) in
            enumerate(shuffled_choices)
            if original_index == correct_index
        )
        dialog = tk.Toplevel(self.root)
        self.bonus_dialog = dialog
        dialog.title(f"Lisäkysymys – tehtävä {self.question_number}")
        dialog.configure(bg=BG)
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.protocol("WM_DELETE_WINDOW", self.close_bonus_dialog)

        tk.Label(dialog, text=f"LISÄKYSYMYS – TEHTÄVÄ {self.question_number}",
                 bg=BG, fg=CYAN, font=("Arial", 14, "bold")).pack(
                     padx=28, pady=(22, 10)
                 )
        tk.Label(dialog, text=question, wraplength=500, justify="left",
                 bg=BG, fg=WHITE, font=("Arial", 12, "bold")).pack(
                     padx=28, pady=(0, 14), anchor="w"
                 )

        self.bonus_choice = tk.IntVar(value=-1)
        self.bonus_choice_buttons = []
        for index, (_original_index, choice) in enumerate(shuffled_choices):
            radio = tk.Radiobutton(
                dialog, text=choice, variable=self.bonus_choice, value=index,
                wraplength=470, justify="left", anchor="w",
                bg=BG, fg=WHITE, selectcolor="#17314f",
                activebackground=BG, activeforeground=WHITE,
                font=("Arial", 11), padx=6, pady=5,
            )
            radio.pack(fill="x", padx=28, anchor="w")
            self.bonus_choice_buttons.append(radio)

        self.bonus_result_label = tk.Label(
            dialog, text="Valitse yksi vaihtoehto.", wraplength=480,
            justify="left", bg=BG, fg=MUTED, font=("Arial", 10),
        )
        self.bonus_result_label.pack(padx=28, pady=(12, 8), anchor="w")

        button_frame = tk.Frame(dialog, bg=BG)
        button_frame.pack(pady=(4, 22))
        self.bonus_submit_button = tk.Button(
            button_frame, text="TARKISTA", command=self.check_bonus_answer,
            font=("Arial", 10, "bold"), cursor="hand2", takefocus=True,
        )
        self.bonus_submit_button.pack(side="left", padx=6, ipadx=20)
        tk.Button(button_frame, text="SULJE", command=self.close_bonus_dialog,
                  font=("Arial", 10, "bold"), cursor="hand2",
                  takefocus=True).pack(side="left", padx=6, ipadx=20)

        self.root.update_idletasks()
        dialog.update_idletasks()
        x = self.root.winfo_rootx() + (
            self.root.winfo_width() - dialog.winfo_width()
        ) // 2
        y = self.root.winfo_rooty() + 100
        dialog.geometry(f"+{max(0, x)}+{max(0, y)}")
        dialog.lift()
        dialog.focus_force()
        # Lisäkysymys ei ota globaalia syötekaappausta. Näin pääikkunan
        # painikkeet eivät voi jäädä lukituiksi, jos ikkuna siirtyy taustalle.

    def check_bonus_answer(self):
        """Palkitsee käsitekysymyksestä kerran ja pienentää pääpalkintoa."""
        if self.bonus_dialog is None or not self.bonus_dialog.winfo_exists():
            return
        selected = self.bonus_choice.get()
        if selected < 0:
            self.bonus_result_label.configure(
                text="Valitse ensin yksi vastausvaihtoehto.", fg=RED
            )
            return
        if selected != self.bonus_correct_index:
            self.bonus_result_label.configure(
                text="Ei aivan. Tutki piiriä ja käsitteitä vielä kerran ja yritä uudelleen.",
                fg=RED,
            )
            return

        if (self.question_number not in self.bonus_tasks
                and self.question_number not in self.scored_tasks):
            self.bonus_tasks.add(self.question_number)
            self.score += BONUS_REWARD
        newly_unlocked = self.update_category_unlocks()
        remaining_reward = 10 - BONUS_REWARD
        self.configure_action_button("bonus", enabled=False,
                                     text="KYSYMYS TEHTY")
        self.bonus_result_label.configure(
            text=(f"Oikein! +{BONUS_REWARD} pistettä. Tämän tehtävän "
                  f"varsinaisesta ratkaisusta saa vielä {remaining_reward} "
                  "pistettä."),
            fg=GREEN,
        )
        for radio in self.bonus_choice_buttons:
            radio.configure(state="disabled")
        self.bonus_submit_button.configure(state="disabled")
        self.message = (f"Lisäkysymys oikein: +{BONUS_REWARD} pistettä. "
                        f"Tehtävän {self.question_number} pääpalkinto on nyt "
                        f"{remaining_reward} pistettä.")
        if newly_unlocked:
            self.message += (" Uusi tehtäväryhmä avautui: "
                             + ", ".join(newly_unlocked) + ".")
        self.message_color = GREEN

    def close_bonus_dialog(self):
        """Sulkee tehtäväkohtaisen lisäkysymysikkunan."""
        if self.bonus_dialog is not None and self.bonus_dialog.winfo_exists():
            self.bonus_dialog.destroy()
        self.bonus_dialog = None
        self.bonus_correct_index = None
        if self.root.winfo_exists():
            self.root.focus_force()

    def open_hint(self):
        """Veloittaa vihjeen ensimmäisestä avaamisesta nykyisessä tehtävänäkymässä."""
        if self.game_completed or self.answer_locked:
            return
        if not self.hint_opened:
            if self.score < HINT_COST:
                self.message = ("Pistemäärä ei riitä vihjeen avaamiseen. "
                                f"Vihje maksaa {HINT_COST} pistettä.")
                self.message_color = RED
                self.flash = -10
                return
            self.score -= HINT_COST
            self.hint_opened = True
            self.message = f"Vihje avattu. −{HINT_COST} pistettä."
            self.message_color = YELLOW
            self.configure_action_button("hint", text="NÄYTÄ VIHJE")
        self.show_hint_dialog()

    def show_hint_dialog(self):
        """Näyttää vihjeen ei-modaalisessa ikkunassa tehtävän ratkaisemisen ajan."""
        if self.hint_dialog is not None and self.hint_dialog.winfo_exists():
            self.hint_dialog.deiconify()
            self.hint_dialog.lift()
            return
        dialog = tk.Toplevel(self.root)
        self.hint_dialog = dialog
        dialog.title(f"Vihje – tehtävä {self.question_number}")
        dialog.configure(bg=BG)
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.protocol("WM_DELETE_WINDOW", self.close_hint_dialog)
        tk.Label(dialog, text=f"VIHJE – TEHTÄVÄ {self.question_number}",
                 bg=BG, fg=CYAN, font=("Arial", 14, "bold")).pack(
                     padx=24, pady=(20, 12)
                 )
        tk.Label(dialog, text=self.hint_for_current_task(), wraplength=430,
                 justify="left", bg=BG, fg=WHITE,
                 font=("Arial", 12)).pack(padx=24, pady=(0, 18))
        tk.Button(dialog, text="SULJE", command=self.close_hint_dialog,
                  font=("Arial", 10, "bold"), cursor="hand2").pack(
                      pady=(0, 20), ipadx=24
                  )
        self.root.update_idletasks()
        dialog.update_idletasks()
        x = self.root.winfo_rootx() + 180
        y = self.root.winfo_rooty() + 150
        dialog.geometry(f"+{max(0, x)}+{max(0, y)}")
        dialog.lift()

    def close_hint_dialog(self):
        """Sulkee näkyvän vihjeen muuttamatta saman tehtävän maksettua tilaa."""
        if self.hint_dialog is not None and self.hint_dialog.winfo_exists():
            self.hint_dialog.destroy()
        self.hint_dialog = None

    def show_concept_information(self, _event=None):
        """Näyttää nykyisen tehtävän ratkaisussa tarvittavan käsitteen."""
        template_number = TASK_TEMPLATE_ORDER[self.question_number - 1]
        info_templates = (ADMITTANCE_INFO_TEMPLATES | NODE_INFO_TEMPLATES
                          | THEVENIN_INFO_TEMPLATES | OPAMP_INFO_TEMPLATES
                          | ELECTRICAL_QUANTITY_INFO_TEMPLATES)
        if template_number not in info_templates:
            return "break"
        if (self.concept_info_dialog is not None
                and self.concept_info_dialog.winfo_exists()):
            self.concept_info_dialog.deiconify()
            self.concept_info_dialog.lift()
            self.concept_info_dialog.focus_force()
            return "break"

        dialog = tk.Toplevel(self.root)
        self.concept_info_dialog = dialog
        sections = []
        if template_number in ELECTRICAL_QUANTITY_INFO_TEMPLATES:
            sections.append(("JÄNNITE- JA VIRTASUUREET", (
                "Lähdejännite on jännitelähteen tuottama jännite. "
                    "Napajännite on jännitelähteen napojen välinen potentiaaliero. "
                "Ideaalisella jännitelähteellä nämä ovat samat. Todellisen "
                "lähteen napajännite voi kuormitettuna olla lähdejännitettä "
                "pienempi lähteen sisäisen resistanssin vuoksi.\n\n"
                "Kokonaisvirta tarkoittaa koko piirin virtaa ennen sen "
                "jakautumista rinnakkaisiin osiin tai niiden yhdistymisen "
                "jälkeen. Se on rinnakkaisten osien virtojen summa. "
                "Pelkkä kokonaisarvo ei ole sähköopin itsenäinen suure: "
                "on kerrottava, tarkoitetaanko esimerkiksi kokonaisvirtaa, "
                "kokonaisresistanssia vai kokonaisimpedanssia.\n\n"
                "Vaihtovirran tehollisarvo on sellaisen tasavirran arvo, "
                "joka tuottaa vastuksessa saman keskimääräisen tehon. "
                "Sinimuotoiselle jännitteelle Ueff = Umax/√2 ja virralle "
                "Ieff = Imax/√2. Tehtävissä ilmoitettu vaihtojännite on "
                "tehollisarvo, ellei toisin mainita. Hetkellisarvo puolestaan "
                "muuttuu ajan mukana, ja huippuarvo on hetkellisarvon suurin "
                "itseisarvo."
            )))
        if template_number in NODE_INFO_TEMPLATES:
            sections.append(("SOLMU JA KIRCHHOFFIN VIRTALAKI", (
                "Solmu on virtapiirin kohta, jossa vähintään kolme haaraa "
                "yhdistyy.\n\n"
                "Kirchhoffin virtalain mukaan solmuun tulevien virtojen "
                "summa on yhtä suuri kuin solmusta lähtevien virtojen summa."
            )))
        if template_number in THEVENIN_INFO_TEMPLATES:
            sections.append(("THÉVENIN-JÄNNITE JA THÉVENIN-VASTUS", (
                "Thévenin-jännite UTh on avoimen lähtöportin A–B välinen "
                "jännite. Avoimeen porttiin ei ole kytketty kuormaa, joten "
                "sen läpi ei kulje virtaa.\n\n"
                "Thévenin-vastus RTh on vastus, joka nähdään katsottaessa "
                "piiriä portista A–B. Sitä määritettäessä riippumaton "
                "ideaalinen jännitelähde korvataan oikosululla ja riippumaton "
                "ideaalinen virtalähde avoimella piirillä. Thévenin-vastus "
                "voidaan määrittää myös suhteesta RTh = UTh/Isc, missä Isc "
                "on portin oikosulkuvirta."
            )))
        if template_number in ADMITTANCE_INFO_TEMPLATES:
            sections.append(("ADMITTANSSI, KONDUKTANSSI JA SUSKEPTANSSI", (
                "Admittanssi Y kertoo, kuinka helposti vaihtovirta kulkee "
                "piirin läpi. Se on impedanssin Z käänteisluku:\n\n"
                "Y = 1/Z\n\n"
                "Admittanssin yksikkö on siemens (S). Vaihtovirtapiirissä "
                "admittanssi esitetään kompleksilukuna, koska virta ja "
                "jännite voivat olla eri vaiheessa. Tällöin Y = G + jB, "
                "missä G on konduktanssi ja B suskeptanssi.\n\n"
                "Konduktanssi G on admittanssin reaaliosa. Se kuvaa "
                "resistiivisen osan kykyä johtaa virtaa. Puhtaalle "
                "vastukselle G = 1/R.\n\n"
                "Suskeptanssi B on admittanssin imaginääriosa. Se kuvaa "
                "kondensaattorien ja käämien vaikutusta vaihtovirran "
                "kulkuun. Merkintätavalla Y = G + jB kondensaattorin "
                "suskeptanssi on positiivinen ja käämin negatiivinen. "
                "Myös konduktanssin ja suskeptanssin yksikkö on siemens (S).\n\n"
                "Admittanssi on erityisen hyödyllinen rinnakkaispiirissä: "
                "rinnakkaisten haarojen admittanssit voidaan summata suoraan."
            )))
        if template_number in OPAMP_INFO_TEMPLATES:
            sections.append(("OPERAATIOVAHVISTIN", (
                "Operaatiovahvistimessa on kaksi tuloa: ei-invertoiva tulo "
                "(+) ja invertoiva tulo (−). Lähtöjännite määräytyy näiden "
                "tulojen jännitteiden erotuksen perusteella.\n\n"
                "Ideaalisen operaatiovahvistimen tuloihin ei kulje virtaa. "
                "Takaisinkytketyssä piirissä operaatiovahvistin voi syöttää "
                "piiriin energiaa ja ylläpitää värähtelyä, jonka taajuuden "
                "määrää varsinainen LC-verkko."
            )))

        if len(sections) == 1:
            heading, explanation = sections[0]
            title = heading.title()
        else:
            title = "Tehtävän käsitteet"
            heading = "LISÄTIETOA"
            explanation = "\n\n".join(
                f"{section_heading}\n{section_text}"
                for section_heading, section_text in sections
            )

        dialog.title(f"Lisätietoa – {title}")
        dialog.configure(bg=BG)
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.protocol("WM_DELETE_WINDOW", self.close_concept_information)

        tk.Label(dialog, text=heading,
                 bg=BG, fg=CYAN, font=("Arial", 14, "bold")).pack(
                     padx=24, pady=(20, 12)
                 )
        text_frame = tk.Frame(dialog, bg=BG)
        text_frame.pack(padx=24, pady=(0, 18), fill="both", expand=True)
        info_text = tk.Text(
            text_frame, width=60, height=20, wrap="word",
            bg=BG, fg=WHITE, font=("Arial", 12), relief="flat",
            borderwidth=0, highlightthickness=0, cursor="arrow",
        )
        scrollbar = tk.Scrollbar(text_frame, command=info_text.yview)
        info_text.configure(yscrollcommand=scrollbar.set)
        info_text.insert("1.0", explanation)
        info_text.configure(state="disabled")
        info_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        tk.Button(dialog, text="SULJE",
                  command=self.close_concept_information,
                  font=("Arial", 10, "bold"), cursor="hand2").pack(
                      pady=(0, 20), ipadx=24
                  )
        self.root.update_idletasks()
        dialog.update_idletasks()
        x = self.root.winfo_rootx() + 180
        y = self.root.winfo_rooty() + 130
        dialog.geometry(f"+{max(0, x)}+{max(0, y)}")
        dialog.lift()
        return "break"

    def close_concept_information(self):
        """Sulkee tehtäväkohtaisen lisätietoikkunan."""
        if (self.concept_info_dialog is not None
                and self.concept_info_dialog.winfo_exists()):
            self.concept_info_dialog.destroy()
        self.concept_info_dialog = None

    def open_solution(self):
        """Veloittaa pisteet, näyttää vastauksen ja lukitsee tehtäväkerran."""
        if self.game_completed or self.answer_locked:
            return
        if not self.solution_revealed:
            if self.score < SOLUTION_COST:
                self.message = ("Pistemäärä ei riitä vastauksen avaamiseen. "
                                f"Oikea vastaus maksaa {SOLUTION_COST} pistettä.")
                self.message_color = RED
                self.flash = -10
                return
            self.score -= SOLUTION_COST
            self.solution_revealed = True
            self.invalidate_solution_attempt()
        self.show_solution_dialog()

    def invalidate_solution_attempt(self):
        """Estää paljastetun vastauksen käyttämisen nykyisillä lähtöarvoilla."""
        self.solution_attempt_invalidated = True
        self.answer_locked = True
        self.answer.set("")
        self.entry.configure(state="disabled")
        self.button.configure(state="disabled")
        self.configure_action_button("bonus", enabled=False)
        self.configure_action_button("hint", enabled=False)
        self.configure_action_button("solution", enabled=False)
        self.message = (f"Oikea vastaus avattu. −{SOLUTION_COST} pistettä. "
                        "Tämä tehtäväkerta on lukittu. Sulje vastausikkuna, "
                        "niin tehtävä saa uudet lähtöarvot.")
        self.message_color = YELLOW

    def show_solution_dialog(self):
        """Näyttää lasketun vastauksen ilman kaavaa, yksikköä tai selitystä."""
        if self.solution_dialog is not None and self.solution_dialog.winfo_exists():
            self.solution_dialog.deiconify()
            self.solution_dialog.lift()
            return
        values = self.challenge.expected_values
        answer_text = "; ".join(f"{value:.1f}" for value in values)
        dialog = tk.Toplevel(self.root)
        self.solution_dialog = dialog
        dialog.title(f"Oikea vastaus – tehtävä {self.question_number}")
        dialog.configure(bg=BG)
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.protocol(
            "WM_DELETE_WINDOW",
            lambda: self.close_solution_dialog(regenerate=True)
        )
        tk.Label(dialog, text="OIKEA VASTAUS", bg=BG, fg=CYAN,
                 font=("Arial", 14, "bold")).pack(padx=30, pady=(20, 12))
        tk.Label(dialog, text=answer_text, bg=BG, fg=WHITE,
                 font=("Arial", 22, "bold")).pack(padx=30, pady=(0, 18))
        tk.Button(
            dialog, text="SULJE",
            command=lambda: self.close_solution_dialog(regenerate=True),
                  font=("Arial", 10, "bold"), cursor="hand2").pack(
                      pady=(0, 20), ipadx=24
                  )
        self.root.update_idletasks()
        dialog.update_idletasks()
        x = self.root.winfo_rootx() + 520
        y = self.root.winfo_rooty() + 170
        dialog.geometry(f"+{max(0, x)}+{max(0, y)}")
        dialog.lift()

    def close_solution_dialog(self, regenerate=False):
        """Sulkee vastausikkunan ja tarvittaessa arpoo tehtävän uudelleen."""
        should_regenerate = (
            regenerate
            and self.solution_revealed
            and self.solution_attempt_invalidated
            and not self.game_completed
            and 1 <= self.question_number <= MAX_TASKS
        )
        current_task = self.question_number
        revealed_values = tuple(
            round(value, 1) for value in self.challenge.expected_values
        )
        old_challenge = self.challenge_signature()
        if (self.solution_dialog is not None
                and self.solution_dialog.winfo_exists()):
            self.solution_dialog.destroy()
        self.solution_dialog = None
        if should_regenerate:
            # Arvotaan sama tehtävä uudelleen. Pelkkä uusi random-valinta ei
            # riitä, sillä se voisi sattumalta palauttaa samat lähtöarvot tai
            # saman numeroarvon, jonka pelaaja juuri näki vastausikkunassa.
            # Hyväksytään uusi tehtäväkerta vasta, kun sekä lähtöarvot että
            # yhden desimaalin tarkkuudella annettava vastaus ovat muuttuneet.
            for _attempt in range(100):
                # new_challenge kasvattaa tehtävänumeroa yhdellä. Peruutetaan
                # numero ensin, jotta sama tehtävätyyppi säilyy.
                self.question_number = current_task - 1
                self.new_challenge(ignore_unlock=True)
                new_values = tuple(
                    round(value, 1) for value in self.challenge.expected_values
                )
                if (self.challenge_signature() != old_challenge
                        and new_values != revealed_values):
                    break
            self.message = (f"Tehtävä {current_task} jatkuu uusilla "
                            "lähtöarvoilla.")
            self.message_color = GREEN

    def challenge_signature(self):
        """Palauttaa kaikki tehtävän lähtöarvot vertailukelpoisena avaimena."""
        challenge = self.challenge
        return (
            challenge.voltages,
            challenge.resistances,
            challenge.sources_parallel,
            challenge.inductance,
            challenge.frequency,
            challenge.capacitances,
            challenge.circuit_type,
            challenge.secondary_inductance,
            challenge.coupling_capacitance,
        )

    def open_task(self, target):
        """Avaa valitun avoinna olevan tehtävän uusilla lähtöarvoilla."""
        if not 1 <= target <= MAX_TASKS:
            return
        if not self.task_is_unlocked(target):
            category = self.category_for_task(target)
            threshold = self.category_threshold(category)
            messagebox.showinfo(
                "Tehtäväryhmä on lukittu",
                f"{self.category_name(category)} avautuvat, kun saavutat "
                f"{threshold} pistettä.",
            )
            return
        if self.next_question_job is not None:
            self.root.after_cancel(self.next_question_job)
            self.next_question_job = None
        self.game_completed = False
        self.highest_unlocked = max(self.highest_unlocked, target)
        self.question_number = target - 1
        self.new_challenge()
        self.message = f"Tehtävä {target} avattu uusilla lähtöarvoilla."
        self.message_color = GREEN

    def finish_game(self):
        """Päättää pelin vasta, kun kaikki 30 tehtävää on ratkaistu oikein."""
        self.next_question_job = None
        self.game_completed = True
        self.answer_locked = True
        self.running = False
        self.close_bonus_dialog()
        self.close_hint_dialog()
        self.close_solution_dialog()
        self.entry.configure(state="disabled")
        self.button.configure(state="disabled")
        self.configure_action_button("bonus", enabled=False)
        self.configure_action_button("hint", enabled=False)
        self.configure_action_button("solution", enabled=False)
        self.message = (f"Onneksi olkoon! Ratkaisit kaikki {MAX_TASKS} "
                        "tehtävää oikein.\n"
                        f"Lopulliset pisteet: {self.score}")
        self.message_color = GREEN

    def check_answer(self):
        # Paljastetulla tehtäväkerralla ei saa suoritusta missään tilanteessa.
        # Tämä erillinen tarkistus suojaa myös mahdollisilta käyttöliittymän
        # tapahtumilta, jotka ehtivät jonoon juuri ennen kentän lukitsemista.
        if (self.answer_locked or self.solution_revealed
                or self.solution_attempt_invalidated):
            return
        raw = self.answer.get().strip().replace(",", ".")
        correct_values = self.challenge.expected_values
        try:
            if len(correct_values) == 1:
                submitted_values = (float(raw),)
            else:
                parts = raw.replace(";", " ").split()
                submitted_values = tuple(float(part) for part in parts)
        except ValueError:
            self.message = ("Kirjoita arvot numeroina. Erota useat vastaukset "
                            "puolipisteillä, esimerkiksi 2,1; 3,4.")
            self.message_color = RED
            self.flash = -12
            return

        expected_values = tuple(round(value, 1) for value in correct_values)
        values_match = (len(submitted_values) == len(expected_values)
                        and all(math.isclose(value, expected, abs_tol=0.01)
                                for value, expected in zip(submitted_values,
                                                           expected_values)))
        if values_match:
            first_scored_completion = self.question_number not in self.scored_tasks
            base_reward = 10
            if self.question_number in self.bonus_tasks:
                base_reward -= BONUS_REWARD
            earned_points = base_reward if first_scored_completion else 0
            if first_scored_completion:
                self.scored_tasks.add(self.question_number)
                self.score += earned_points
            newly_unlocked = self.update_category_unlocks()
            self.answer_locked = True
            self.entry.configure(state="disabled")
            self.button.configure(state="disabled")
            self.configure_action_button("bonus", enabled=False)
            self.configure_action_button("hint", enabled=False)
            self.configure_action_button("solution", enabled=False)
            self.level = 2 if self.question_number >= 1 else 1
            self.running = True
            if self.challenge.circuit_type.startswith("ac_"):
                impedance = self.challenge.complex_impedance
                calculation = (f"Z={impedance.real:.2f} "
                               f"{impedance.imag:+.2f}j Ω, |Z|="
                               f"{abs(impedance):.2f} Ω")
            elif self.challenge.circuit_type == "three_source_mesh":
                calculation = ("Kirchhoffin solmulaki: I1+I2+I3=0; "
                               "haaravirtojen merkit kertovat suunnan")
            elif self.challenge.circuit_type == "lc_oscillator":
                c1, c2 = self.challenge.capacitances
                equivalent = c1 * c2 / (c1 + c2)
                calculation = (f"Ceq={equivalent * 1e9:.2f} nF ja "
                               "f=1/(2π√(LCeq))")
            elif self.challenge.circuit_type == "nodal_voltages":
                calculation = "Solmujen V1 ja V2 Kirchhoffin virtayhtälöistä"
            elif self.challenge.circuit_type == "bridge_currents":
                calculation = "Siltapiirin kolmen solmujännitteen avulla"
            elif self.challenge.circuit_type.startswith("thevenin_"):
                _, series, branch, output = self.challenge.resistances
                parallel_resistance = series * branch / (series + branch)
                if self.challenge.circuit_type == "thevenin_voltage":
                    calculation = (f"Uth={self.challenge.voltage}·{branch}/"
                                   f"({series}+{branch})")
                elif self.challenge.circuit_type == "thevenin_short_current":
                    load = branch * output / (branch + output)
                    calculation = (f"R3‖R4={load:g} Ω ja "
                                   f"Isc=Usolmu/{output}")
                elif self.challenge.circuit_type == "thevenin_parallel":
                    calculation = f"{series} Ω ‖ {branch} Ω"
                else:
                    calculation = (f"{output} Ω + ({series} Ω ‖ "
                                   f"{branch} Ω = {parallel_resistance:g} Ω)")
            elif self.challenge.circuit_type == "kirchhoff_parallel":
                r1, r2, r3 = self.challenge.resistances
                i1 = self.challenge.voltage / r1
                i2 = self.challenge.voltage / r2
                i3 = self.challenge.voltage / r3
                calculation = (f"I1={i1:g} A, I2={i2:g} A, I3={i3:g} A, "
                               f"I={i1+i2+i3:g} A")
            elif self.challenge.circuit_type == "coupled_lc":
                calculation = "Piirin kompleksisten haara-admittanssien avulla"
            elif self.challenge.circuit_type == "kirchhoff":
                r1, r2, r3 = self.challenge.resistances
                parallel_r = (r2 * r3) / (r2 + r3)
                calculation = (f"R2‖R3={parallel_r:g} Ω, "
                               f"Rkok={self.challenge.resistance:g} Ω, "
                               f"{self.challenge.voltage} V / {self.challenge.resistance:g} Ω")
            elif self.challenge.capacitances:
                calculation = (f"C={self.challenge.capacitance * 1e6:g} µF, "
                               f"XC={self.challenge.capacitive_reactance:.2f} Ω, "
                               f"Z={self.challenge.impedance:.2f} Ω, "
                               f"{self.challenge.voltage} V / {self.challenge.impedance:.2f} Ω")
            elif self.challenge.inductance:
                calculation = (f"XL={self.challenge.inductive_reactance:.2f} Ω, "
                               f"Z={self.challenge.impedance:.2f} Ω, "
                               f"{self.challenge.voltage} V / {self.challenge.impedance:.2f} Ω")
            elif len(self.challenge.voltages) == 1:
                calculation = f"{self.challenge.voltage} V / {self.challenge.resistance} Ω"
            elif len(self.challenge.resistances) == 1:
                u1, u2 = self.challenge.voltages
                calculation = f"({u1} V + {u2} V) / {self.challenge.resistance} Ω"
            else:
                resistance_list = " ‖ ".join(f"{r} Ω" for r in self.challenge.resistances)
                if self.challenge.sources_parallel:
                    voltage_part = f"{self.challenge.voltage} V"
                else:
                    u1, u2 = self.challenge.voltages
                    voltage_part = f"({u1} V + {u2} V)"
                calculation = (f"{voltage_part} / ({resistance_list} = "
                               f"{self.challenge.resistance:g} Ω)")
            answer_text = "; ".join(f"{expected:.1f}"
                                    for expected in expected_values)
            unit = self.challenge.answer_unit
            if earned_points:
                score_message = f"+{earned_points} pistettä"
            else:
                score_message = ("Tästä tehtävästä on jo saatu piste – "
                                 "ei lisäpistettä")
            self.message = (f"Oikein! {calculation} = {answer_text} {unit}\n"
                            f"{score_message}")
            if newly_unlocked:
                self.message += ("\nUusi tehtäväryhmä avautui: "
                                 + ", ".join(newly_unlocked) + ".")
            self.message_color = GREEN
            self.flash = 24
            self.canvas.itemconfigure(self.current_text, text="")
            self.spawn_particles()
            all_tasks_completed = len(self.scored_tasks) == MAX_TASKS
            if all_tasks_completed:
                self.game_completed = True
                self.next_question_job = self.root.after(1600, self.finish_game)
            elif self.question_number < MAX_TASKS:
                self.next_question_job = self.root.after(1600, self.new_challenge)
            else:
                remaining = MAX_TASKS - len(self.scored_tasks)
                self.message += (f"\nPeli ei ole vielä läpäisty: "
                                 f"{remaining} tehtävää puuttuu.")
        else:
            self.wrong_attempts += 1
            self.running = False
            if self.wrong_attempts >= 3:
                self.answer_locked = True
                self.answer.set("")
                self.entry.configure(state="disabled")
                self.button.configure(state="disabled")
                self.message = ("Kolme numeerista mutta virheellistä yritystä. "
                                "Pisteitä ei vähennetä. Tehtävä avataan nyt "
                                "uusilla lähtöarvoilla.")
                self.message_color = YELLOW
                self.canvas.update_idletasks()
                self.reroll_after_wrong_attempts()
                return
            if self.challenge.circuit_type.startswith("ac_"):
                self.message = ("Ei aivan. Laske ensin piirin "
                                "kompleksinen kokonaisimpedanssi ja jaa "
                                "jännitteen tehollisarvo sen itseisarvolla.")
            elif self.challenge.circuit_type == "three_source_mesh":
                self.message = ("Ei aivan. Valitse ylä- ja "
                                "alasolmun välinen jännite ja kirjoita jokaisen "
                                "haaran jänniteyhtälö samalla virran suunnalla.")
            elif self.challenge.circuit_type == "lc_oscillator":
                self.message = ("Ei aivan. Muodosta ensin "
                                "C1:n ja C2:n sarjakapasitanssi ja käytä sitä "
                                "LC-piirin resonanssitaajuudessa.")
            elif self.challenge.circuit_type == "nodal_voltages":
                self.message = ("Ei aivan. Muodosta Kirchhoffin "
                                "virtayhtälöt solmuille V1 ja V2.")
            elif self.challenge.circuit_type == "bridge_currents":
                self.message = ("Ei aivan. Ratkaise ensin sillan "
                                "kolme solmujännitettä ja laske haaravirrat.")
            elif self.challenge.circuit_type.startswith("thevenin_"):
                self.message = ("Ei aivan. Tarkista porttien A–B "
                                "näkemä kytkentä ja sarja- sekä rinnankytkennät.")
            elif self.challenge.circuit_type == "coupled_lc":
                self.message = ("Ei aivan. Laske LC-haarojen "
                                "kompleksiset admittanssit ja huomioi Cg.")
            elif self.challenge.circuit_type == "kirchhoff_parallel":
                self.message = "Ei aivan. Kokonaisvirta on haaravirtojen summa."
            elif self.challenge.circuit_type == "kirchhoff":
                self.message = "Ei aivan. Tarkista solmujen ja silmukoiden virrat."
            elif self.challenge.capacitances:
                self.message = "Ei aivan. Huomioi rinnankytketyt kapasitanssit."
            elif self.challenge.inductance:
                self.message = "Ei aivan. Vihje: XL=2πfL ja Z=√(R²+XL²)."
            elif len(self.challenge.resistances) >= 2:
                self.message = ("Ei aivan. "
                                "Vihje: 1/Rkok = 1/R1 + 1/R2 + …")
            else:
                self.message = ("Ei aivan. "
                                "Vihje: jaa jännite vastuksella. Yritä uudelleen!")
            self.message += (f"\nVirheellinen yritys {self.wrong_attempts}/3. "
                             "Pisteitä ei vähennetä.")
            self.message_color = RED
            self.flash = -18

    def reroll_after_wrong_attempts(self):
        """Arpoo saman tehtävän uudelleen kolmannen väärän vastauksen jälkeen."""
        task_number = self.question_number
        self.open_task(task_number)
        self.message = (f"Tehtävä {task_number} avattiin uusilla "
                        "lähtöarvoilla kolmen virheellisen yrityksen jälkeen. "
                        "Pisteitä ei vähennetty.")
        self.message_color = YELLOW

    def spawn_particles(self):
        for _ in range(35):
            self.particles.append([350, 335, random.uniform(-4, 4), random.uniform(-5, 1),
                                   random.randint(20, 45), random.choice([CYAN, YELLOW, GREEN])])

    @staticmethod
    def circuit_point(t):
        # Piste suorakulmaisen johdon kehällä.
        left, right, top, bottom = 130, 570, 205, 465
        lengths = [right-left, bottom-top, right-left, bottom-top]
        distance = (t % 1) * sum(lengths)
        if distance < lengths[0]:
            return left + distance, top
        distance -= lengths[0]
        if distance < lengths[1]:
            return right, top + distance
        distance -= lengths[1]
        if distance < lengths[2]:
            return right - distance, bottom
        distance -= lengths[2]
        return left, bottom - distance

    def draw_circuit(self):
        self.canvas.delete("animated")
        glow = CYAN if self.running else "#31506b"
        width = 5 if self.running else 3

        if self.challenge.circuit_type.startswith("ac_"):
            self.draw_ac_network_circuit(glow, width)
            return
        if self.challenge.circuit_type == "three_source_mesh":
            self.draw_three_source_mesh_circuit(glow, width)
            return
        if self.challenge.circuit_type == "lc_oscillator":
            self.draw_lc_oscillator_circuit(glow, width)
            return
        if self.challenge.circuit_type == "kirchhoff":
            self.draw_kirchhoff_circuit(glow, width)
            return
        if self.challenge.circuit_type == "kirchhoff_parallel":
            self.draw_parallel_kirchhoff_circuit(glow, width)
            return
        if self.challenge.circuit_type == "coupled_lc":
            self.draw_coupled_lc_circuit(glow, width)
            return
        if self.challenge.circuit_type.startswith("thevenin_"):
            self.draw_thevenin_circuit(glow, width)
            return
        if self.challenge.circuit_type == "nodal_voltages":
            self.draw_nodal_voltage_circuit(glow, width)
            return
        if self.challenge.circuit_type == "bridge_currents":
            self.draw_bridge_circuit(glow, width)
            return

        # Pääjohdot piirretään osina. Rinnankytkennän kahden solmun välissä
        # ei saa olla ylimääräistä suoraa johtoa: siellä ovat vain komponenttihaarat.
        if self.challenge.inductance or self.challenge.capacitances:
            self.canvas.create_line(130, 205, 300, 205, fill=glow, width=width,
                                    tags="animated")
            self.canvas.create_line(440, 205, 570, 205, fill=glow, width=width,
                                    tags="animated")
            if self.challenge.inductance:
                self.draw_inductor(300, 440, 205)
            else:
                self.draw_horizontal_resistor(300, 440, 205)
        else:
            self.canvas.create_line(130, 205, 570, 205, fill=glow, width=width,
                                    tags="animated")
        self.canvas.create_line(130, 465, 570, 465, fill=glow, width=width,
                                tags="animated")

        if self.challenge.sources_parallel:
            self.canvas.create_line(130, 205, 130, 245, fill=glow, width=width,
                                    tags="animated")
            self.canvas.create_line(130, 425, 130, 465, fill=glow, width=width,
                                    tags="animated")
        else:
            self.canvas.create_line(130, 205, 130, 465, fill=glow, width=width,
                                    tags="animated")

        if len(self.challenge.resistances) > 1 or self.challenge.capacitances:
            self.canvas.create_line(570, 205, 570, 245, fill=glow, width=width,
                                    tags="animated")
            self.canvas.create_line(570, 425, 570, 465, fill=glow, width=width,
                                    tags="animated")
        else:
            self.canvas.create_line(570, 205, 570, 465, fill=glow, width=width,
                                    tags="animated")

        if len(self.challenge.voltages) == 1:
            if self.challenge.frequency:
                self.draw_ac_source(130, 350)
            else:
                self.draw_battery(130, 350)
        elif self.challenge.sources_parallel:
            # Pääjohto liittyy keskellä olevaan solmuun. Molemmat lähteet ovat
            # samanarvoisissa sivuhaaroissa yhteisten ylä- ja alasolmujen välissä.
            source_x = self.parallel_positions("source", len(self.challenge.voltages))
            self.canvas.create_line(source_x[0], 245, source_x[-1], 245,
                                    fill=glow, width=width,
                                    tags="animated")
            self.canvas.create_line(source_x[0], 425, source_x[-1], 425,
                                    fill=glow, width=width,
                                    tags="animated")
            for x in source_x:
                self.canvas.create_line(x, 245, x, 425, fill=glow, width=width,
                                        tags="animated")
                self.draw_battery(x, 335)
        else:
            self.draw_battery(130, 290)
            self.draw_battery(130, 410)
            self.canvas.create_text(172, 290, anchor="w", text=f"{self.challenge.voltages[0]} V",
                                    fill=YELLOW, font=("Arial", 11, "bold"), tags="animated")
            self.canvas.create_text(172, 410, anchor="w", text=f"{self.challenge.voltages[1]} V",
                                    fill=YELLOW, font=("Arial", 11, "bold"), tags="animated")

        # Kondensaattoritehtävässä vastus on pääjohdolla ja kondensaattorit rinnan.
        if self.challenge.capacitances:
            branch_x = self.parallel_positions("capacitor", len(self.challenge.capacitances))
            self.canvas.create_line(branch_x[0], 245, branch_x[-1], 245,
                                    fill=glow, width=width, tags="animated")
            self.canvas.create_line(branch_x[0], 425, branch_x[-1], 425,
                                    fill=glow, width=width, tags="animated")
            for x in branch_x:
                self.canvas.create_line(x, 245, x, 425, fill=glow, width=width,
                                        tags="animated")
                self.draw_capacitor(x, 335)
        elif len(self.challenge.resistances) == 1:
            self.draw_resistor(570, 325)
        else:
            # Pääjohto saapuu keskellä olevaan solmuun. Yksikään vastus ei ole
            # pääjohdon jatkeena, joten haarat näyttävät keskenään samanarvoisilta.
            branch_x = self.parallel_positions("resistor", len(self.challenge.resistances))
            left_x = branch_x[0]
            right_x = branch_x[-1]
            self.canvas.create_line(left_x, 245, right_x, 245, fill=glow, width=width,
                                    tags="animated")
            self.canvas.create_line(left_x, 425, right_x, 425, fill=glow, width=width,
                                    tags="animated")
            for x in branch_x:
                self.canvas.create_line(x, 245, x, 425, fill=glow, width=width,
                                        tags="animated")
                self.draw_resistor(x, 335)

        # Lamppu kuuluu aiempiin tehtäviin; RL-tehtävässä näytetään vain R ja L.
        if not self.challenge.inductance and not self.challenge.capacitances:
            pulse = (math.sin(self.phase * 3) + 1) / 2
            radius = 46 + pulse * 8 if self.running else 42
            lamp_color = YELLOW if self.running else "#627080"
            if self.running:
                self.canvas.create_oval(350-radius, 335-radius, 350+radius, 335+radius,
                                        fill="#4c4320", outline="", tags="animated")
            self.canvas.create_oval(310, 295, 390, 375, fill="#172337", outline=lamp_color,
                                    width=5, tags="animated")
            self.canvas.create_line(328, 320, 350, 350, 372, 320, fill=lamp_color, width=4,
                                    tags="animated")
            self.canvas.create_text(350, 400, text="LAMPPU", fill=MUTED,
                                    font=("Arial", 11, "bold"), tags="animated")

        # Liikkuvat elektronit
        for t in self.electrons:
            x, y = self.circuit_point(t)
            if ((len(self.challenge.resistances) > 1 or self.challenge.capacitances)
                    and x == 570 and 245 < y < 425):
                continue
            if self.challenge.sources_parallel and x == 130 and 245 < y < 425:
                continue
            self.canvas.create_oval(x-5, y-5, x+5, y+5, fill=WHITE, outline=CYAN,
                                    width=2, tags="animated")

        # Rinnankytkennässä elektronit liikkuvat jokaisessa haarassa.
        if len(self.challenge.resistances) > 1 or self.challenge.capacitances:
            if self.challenge.capacitances:
                branch_x = self.parallel_positions("capacitor", len(self.challenge.capacitances))
            else:
                branch_x = self.parallel_positions("resistor", len(self.challenge.resistances))
            if self.challenge.capacitances:
                branch_currents = [
                    2 * math.pi * self.challenge.frequency
                    * capacitance * self.challenge.voltage
                    for capacitance in self.challenge.capacitances
                ]
            else:
                branch_currents = [self.challenge.voltage / resistance
                                   for resistance in self.challenge.resistances]
            largest_branch_current = max(branch_currents)
            for branch_index, (x, branch_current) in enumerate(
                    zip(branch_x, branch_currents)):
                if self.challenge.capacitances:
                    # Elektronit värähtelevät levyille asti, mutta eivät kulje eristeen läpi.
                    motion = 18 * math.sin(self.phase * 3 + branch_index)
                    # Tiheys lasketaan koko 180 pikselin haaran pituudella,
                    # vaikka hiukkaset pysähtyvät kondensaattorin levyille.
                    route = [(x, 245), (x, 425)]
                    count = self.relative_particle_count(
                        branch_current, largest_branch_current, route, minimum=2
                    )
                    for index in range(count):
                        spread = (index-(count-1)/2) * 10
                        for y in (280 + motion + spread, 390 - motion - spread):
                            self.canvas.create_oval(x-5, y-5, x+5, y+5,
                                                    fill=WHITE, outline=CYAN,
                                                    width=2, tags="animated")
                else:
                    route = [(x, 245), (x, 425)]
                    count = self.relative_particle_count(
                        branch_current, largest_branch_current, route, minimum=2
                    )
                    for electron_index in range(count):
                        offset = electron_index * 180 / count + branch_index * 15
                        y = 245 + (self.branch_flow + offset) % 180
                        self.canvas.create_oval(x-5, y-5, x+5, y+5, fill=WHITE,
                                                outline=CYAN, width=2, tags="animated")

        # Lähdepuolella virta jakautuu molempiin rinnakkaisiin lähdehaaroihin.
        if self.challenge.sources_parallel:
            source_x = self.parallel_positions("source", len(self.challenge.voltages))
            # Samanarvoiset ideaalilähteet oletetaan kuormaa tasan jakaviksi.
            source_currents = [self.challenge.current / len(source_x)] * len(source_x)
            largest_source_current = max(source_currents)
            for branch_index, x in enumerate(source_x):
                route = [(x, 245), (x, 425)]
                count = self.relative_particle_count(
                    source_currents[branch_index], largest_source_current,
                    route, minimum=2,
                )
                for electron_index in range(count):
                    offset = electron_index * 180 / count + branch_index * 20
                    y = 425 - (self.branch_flow + offset) % 180
                    self.canvas.create_oval(x-5, y-5, x+5, y+5, fill=WHITE,
                                            outline=CYAN, width=2, tags="animated")

        for particle in self.particles:
            x, y, _, _, life, color = particle
            r = max(2, life / 10)
            self.canvas.create_oval(x-r, y-r, x+r, y+r, fill=color, outline="", tags="animated")

    def draw_battery(self, x, y):
        """Piirtää standardin paristosymbolin pystysuuntaiseen johtoon."""
        self.draw_vertical_voltage_source(x, y, positive_top=True)

    def draw_ac_source(self, x, y):
        """Piirtää vaihtojännitelähteen ilman kiinteitä plus- ja miinusnapoja."""
        self.canvas.create_oval(x-35, y-35, x+35, y+35, fill=PANEL,
                                outline=YELLOW, width=4, tags="animated")
        wave = []
        for step in range(41):
            ratio = step / 40
            wave_x = x - 23 + 46 * ratio
            wave_y = y - 11 * math.sin(ratio * 2 * math.pi)
            wave.append((wave_x, wave_y))
        self.canvas.create_line(wave, fill=YELLOW, width=4, smooth=True,
                                tags="animated")

    @staticmethod
    def polyline_point(points, position):
        """Palauttaa pisteen murtoviivalta animaatiota varten."""
        segments = []
        total = 0.0
        for start, end in zip(points, points[1:]):
            length = math.hypot(end[0] - start[0], end[1] - start[1])
            segments.append((start, end, length))
            total += length
        distance = (position % 1.0) * total
        for start, end, length in segments:
            if distance <= length:
                ratio = distance / length if length else 0
                return (start[0] + (end[0] - start[0]) * ratio,
                        start[1] + (end[1] - start[1]) * ratio)
            distance -= length
        return points[-1]

    def draw_kirchhoff_circuit(self, glow, width):
        """Piirtää kaksi silmukkaa sekä virran jakautumisen solmuissa B ja E."""
        a, b, c = (130, 220), (420, 220), (570, 220)
        f, e, d = (130, 450), (420, 450), (570, 450)

        # Johtimet muodostavat kaksi silmukkaa ja yhteisen B–E-haaran.
        self.canvas.create_line(a, b, c, d, e, f, a, fill=glow, width=width,
                                joinstyle="round", tags="animated")
        self.canvas.create_line(b, e, fill=glow, width=width, tags="animated")
        self.draw_battery(130, 335)
        self.draw_horizontal_resistor(220, 340, 220)
        self.draw_resistor(420, 335)
        self.draw_resistor(570, 335)

        r1, r2, r3 = self.challenge.resistances
        self.canvas.create_text(280, 185, text=f"R1  {r1} Ω", fill=YELLOW,
                                font=("Arial", 11, "bold"), tags="animated")
        self.canvas.create_text(390, 335, anchor="e", text=f"R2\n{r2} Ω", fill=YELLOW,
                                font=("Arial", 10, "bold"), tags="animated")
        self.canvas.create_text(595, 335, anchor="w", text=f"R3\n{r3} Ω", fill=YELLOW,
                                font=("Arial", 10, "bold"), tags="animated")

        label_offsets = {
            "A": (-16, -17), "B": (-12, -20), "C": (14, -17),
            "D": (15, 17), "E": (-13, 18), "F": (-16, 17),
        }
        for label, (x, y) in [("A", a), ("B", b), ("C", c),
                              ("D", d), ("E", e), ("F", f)]:
            dx, dy = label_offsets[label]
            self.canvas.create_text(x+dx, y+dy, text=label, fill=WHITE,
                                    font=("Arial", 12, "bold"), tags="animated")
            self.canvas.create_oval(x-6, y-6, x+6, y+6, fill=WHITE, outline=CYAN,
                                    width=2, tags="animated")

        self.canvas.create_text(275, 360, text="SILMUKKA 1", fill=MUTED,
                                font=("Arial", 11, "bold"), tags="animated")
        self.canvas.create_text(500, 360, text="SILMUKKA 2", fill=MUTED,
                                font=("Arial", 11, "bold"), tags="animated")

        if self.running:
            parallel_resistance = r2 * r3 / (r2 + r3)
            total_current = self.challenge.voltage / (r1 + parallel_resistance)
            branch_voltage = total_current * parallel_resistance
            i2, i3 = branch_voltage / r2, branch_voltage / r3
            self.draw_closed_current_particles([
                (i2, [e, f, a, b, e]),
                (i3, [e, f, a, b, c, d, e]),
            ])

        for particle in self.particles:
            x, y, _, _, life, color = particle
            radius = max(2, life / 10)
            self.canvas.create_oval(x-radius, y-radius, x+radius, y+radius,
                                    fill=color, outline="", tags="animated")

    def draw_parallel_kirchhoff_circuit(self, glow, width):
        """Piirtää kolme rinnakkaista haaraa ja Kirchhoffin solmuvirrat."""
        top, bottom = 220, 450
        branch_x = [180, 320, 460]
        source_x = 570

        self.canvas.create_line(branch_x[0], top, source_x, top, fill=glow,
                                width=width, tags="animated")
        self.canvas.create_line(branch_x[0], bottom, source_x, bottom, fill=glow,
                                width=width, tags="animated")
        for x in branch_x:
            self.canvas.create_line(x, top, x, bottom, fill=glow, width=width,
                                    tags="animated")
            self.draw_resistor(x, 325)
        self.canvas.create_line(source_x, top, source_x, bottom, fill=glow,
                                width=width, tags="animated")

        # Lähteen plusnapa on alhaalla mallikuvan mukaisesti. Käytetään samaa
        # standardoitua paristosymbolia kuin pelin muissa tasajännitetehtävissä.
        self.draw_vertical_voltage_source(source_x, 335, positive_top=False)
cd 
        for index, x in enumerate(branch_x, 1):
            self.canvas.create_text(x-28, 325, anchor="e", text=f"R{index}",
                                    fill=YELLOW, font=("Arial", 10, "bold"),
                                    tags="animated")

        # Solmut korostavat yhteistä ylä- ja alajohdinta.
        for x in branch_x:
            for y in (top, bottom):
                self.canvas.create_oval(x-6, y-6, x+6, y+6, fill=WHITE,
                                        outline=CYAN, width=2, tags="animated")

        if self.running:
            branch_currents = [self.challenge.voltage / resistance
                               for resistance in self.challenge.resistances]
            routes = [
                (current, [(source_x, bottom), (x, bottom),
                           (x, top), (source_x, top), (source_x, bottom)])
                for x, current in zip(branch_x, branch_currents)
            ]
            self.draw_closed_current_particles(routes)

        for particle in self.particles:
            x, y, _, _, life, color = particle
            radius = max(2, life / 10)
            self.canvas.create_oval(x-radius, y-radius, x+radius, y+radius,
                                    fill=color, outline="", tags="animated")

    def draw_nodal_voltage_circuit(self, glow, width):
        """Piirtää kahden tuntemattoman solmujännitteen vastusverkon."""
        source_x, node1_x, node2_x = 145, 355, 555
        main_y, upper_y, bottom = 245, 175, 450
        r1, r2, r3, r4, r5 = self.challenge.resistances

        self.canvas.create_line(source_x, main_y, 225, main_y, fill=glow,
                                width=width, tags="animated")
        self.draw_horizontal_resistor(225, 315, main_y)
        self.canvas.create_line(315, main_y, node1_x, main_y, fill=glow,
                                width=width, tags="animated")
        self.canvas.create_line(node1_x, main_y, 420, main_y, fill=glow,
                                width=width, tags="animated")
        self.draw_horizontal_resistor(420, 510, main_y)
        self.canvas.create_line(510, main_y, node2_x, main_y, fill=glow,
                                width=width, tags="animated")

        self.canvas.create_line(source_x, main_y, source_x, upper_y, 260, upper_y,
                                fill=glow, width=width, tags="animated")
        self.draw_horizontal_resistor(260, 440, upper_y)
        self.canvas.create_line(440, upper_y, node2_x, upper_y, node2_x, main_y,
                                fill=glow, width=width, tags="animated")
        self.canvas.create_line(source_x, main_y, source_x, bottom, node2_x, bottom,
                                fill=glow, width=width, tags="animated")
        self.canvas.create_line(node1_x, main_y, node1_x, bottom, fill=glow,
                                width=width, tags="animated")
        self.canvas.create_line(node2_x, main_y, node2_x, bottom, fill=glow,
                                width=width, tags="animated")
        self.draw_battery(source_x, 350)
        self.draw_resistor(node1_x, 350)
        self.draw_resistor(node2_x, 350)

        labels = [(270, 215, f"R1 {r1} Ω"), (465, 215, f"R2 {r2} Ω"),
                  (350, 140, f"R3 {r3} Ω"), (390, 350, f"R4 {r4} Ω"),
                  (590, 350, f"R5 {r5} Ω")]
        for x, y, label in labels:
            self.canvas.create_text(x, y, text=label, fill=YELLOW,
                                    font=("Arial", 9, "bold"), tags="animated")
        for x, name in ((node1_x, "V1"), (node2_x, "V2")):
            self.canvas.create_oval(x-6, main_y-6, x+6, main_y+6, fill=WHITE,
                                    outline=CYAN, width=2, tags="animated")
            label_x = x + 24 if name == "V2" else x
            self.canvas.create_text(label_x, main_y-28, text=name, fill=WHITE,
                                    font=("Arial", 11, "bold"), tags="animated")

        if self.running:
            v1, v2 = self.challenge.expected_values
            # Piiri hajotetaan kolmeen suljettuun virtasilmukkaan. Niiden
            # päällekkäisyys tuottaa yhteisillä johdoilla oikean summavirran.
            closed_routes = [
                (v1/r4,
                 [(source_x, bottom), (source_x, main_y),
                  (node1_x, main_y), (node1_x, bottom), (source_x, bottom)]),
                ((v1-v2)/r2,
                 [(source_x, bottom), (source_x, main_y),
                  (node1_x, main_y), (node2_x, main_y),
                  (node2_x, bottom), (source_x, bottom)]),
                ((self.challenge.voltage-v2)/r3,
                 [(source_x, bottom), (source_x, main_y),
                  (source_x, upper_y), (node2_x, upper_y),
                  (node2_x, main_y), (node2_x, bottom),
                  (source_x, bottom)]),
            ]
            self.draw_closed_current_particles(closed_routes, minimum=4)

    def draw_bridge_circuit(self, glow, width):
        """Piirtää kuuden vastuksen siltapiirin ja kaikki haaravirrat."""
        source_top, top = (145, 210), (380, 210)
        left, right, bottom = (270, 335), (490, 335), (380, 460)
        source_bottom = (145, 460)
        rs, r1, r2, r3, r4, r5 = self.challenge.resistances

        self.canvas.create_line(source_bottom, source_top, fill=glow, width=width,
                                tags="animated")
        self.draw_battery(145, 335)
        self.canvas.create_line(source_top, 205, 210, fill=glow, width=width,
                                tags="animated")
        self.draw_resistor_between((205, 210), (320, 210))
        self.canvas.create_line(320, 210, top, fill=glow, width=width,
                                tags="animated")
        self.draw_resistor_between(top, left)
        self.draw_resistor_between(top, right)
        self.draw_resistor_between(left, bottom)
        self.draw_resistor_between(right, bottom)
        self.draw_resistor_between(left, right)
        self.canvas.create_line(bottom, source_bottom, fill=glow, width=width,
                                tags="animated")

        labels = [(260, 175, f"Rs {rs} Ω"), (305, 250, f"R1 {r1} Ω"),
                  (455, 250, f"R2 {r2} Ω"), (300, 415, f"R3 {r3} Ω"),
                  (460, 415, f"R4 {r4} Ω"), (380, 310, f"R5 {r5} Ω")]
        for x, y, label in labels:
            self.canvas.create_text(x, y, text=label, fill=YELLOW,
                                    font=("Arial", 9, "bold"), tags="animated")
        for point in (top, left, right, bottom):
            x, y = point
            self.canvas.create_oval(x-6, y-6, x+6, y+6, fill=WHITE,
                                    outline=CYAN, width=2, tags="animated")

        if self.running:
            source = self.challenge.voltage
            matrix = (
                (1/rs + 1/r1 + 1/r2, -1/r1, -1/r2),
                (-1/r1, 1/r1 + 1/r3 + 1/r5, -1/r5),
                (-1/r2, -1/r5, 1/r2 + 1/r4 + 1/r5),
            )
            vt, vl, vr = Challenge.solve_linear(matrix, (source/rs, 0, 0))
            i1, i2 = (vt-vl)/r1, (vt-vr)/r2
            i3, i4, i5 = vl/r3, vr/r4, (vl-vr)/r5
            prefix = [source_bottom, source_top, top]
            if i5 >= 0:
                closed_routes = [
                    (i3, prefix + [left, bottom, source_bottom]),
                    (i2, prefix + [right, bottom, source_bottom]),
                    (i5, prefix + [left, right, bottom, source_bottom]),
                ]
            else:
                closed_routes = [
                    (i1, prefix + [left, bottom, source_bottom]),
                    (i4, prefix + [right, bottom, source_bottom]),
                    (-i5, prefix + [right, left, bottom, source_bottom]),
                ]
            self.draw_closed_current_particles(closed_routes)

    def draw_closed_current_particles(self, routes, minimum=2):
        """Animoi virta ja huomioi sekä virran suuruuden että reitin pituuden."""
        nonzero = [(current, route) for current, route in routes
                   if current > 1e-9]
        if not nonzero:
            return
        largest = max(current for current, _route in nonzero)
        flow = (self.branch_flow / 180) % 1
        for route_index, (current, route) in enumerate(nonzero):
            count = self.relative_particle_count(current, largest, route, minimum)
            for index in range(count):
                position = flow + index / count + route_index * 0.05
                x, y = self.polyline_point(route, position)
                self.canvas.create_oval(x-5, y-5, x+5, y+5, fill=WHITE,
                                        outline=CYAN, width=2, tags="animated")

    def draw_ac_phasor_particles(self, routes, minimum=2):
        """Animoi AC-haarat niiden virtojen suhteellisilla vaiheilla ja tiheyksillä."""
        nonzero = [(current, route) for current, route in routes
                   if abs(current) > 1e-9]
        if not nonzero:
            return
        largest = max(abs(current) for current, _route in nonzero)
        for route_index, (current, route) in enumerate(nonzero):
            count = self.relative_particle_count(abs(current), largest, route,
                                                 minimum)
            phase_angle = math.atan2(current.imag, current.real)
            displacement = 0.10*math.sin(self.phase*2 + phase_angle)
            for index in range(count):
                position = index/count + displacement + route_index*0.025
                x, y = self.polyline_point(route, position)
                self.canvas.create_oval(x-5, y-5, x+5, y+5, fill=WHITE,
                                        outline=CYAN, width=2, tags="animated")

    @staticmethod
    def relative_particle_count(current, largest_current, route, minimum=2):
        """Muuttaa suhteellisen haaravirran reitin pituutta vastaavaksi tiheydeksi."""
        if current <= 1e-9 or largest_current <= 1e-9:
            return 0
        route_length = sum(
            math.hypot(end[0]-start[0], end[1]-start[1])
            for start, end in zip(route, route[1:])
        )
        proportional_count = round(
            2.0 * (current / largest_current) * (route_length / 100)
        )
        return min(18, max(minimum, proportional_count))

    def mask_component_line(self, start, end):
        """Peittää komponentin alta johdon kaikissa kaavioissa.

        Kaavioalueen taustavärinen viiva piirretään ensin hieman johtoa
        paksumpana. Sen jälkeen varsinainen komponenttisymboli voidaan piirtää
        ilman, että aiemmin luotu virtapiirin runko näkyy symbolin läpi.
        """
        # Jata peitto nelja pikselia komponentin paatepisteiden sisapuolelle.
        # Komponentin keltainen paaty ja johdin menevat silloin hieman
        # paallekkain, eika rasterointi voi synnyttaa niiden valiin rakoa.
        x1, y1 = start
        x2, y2 = end
        dx, dy = x2-x1, y2-y1
        length = math.hypot(dx, dy)
        inset = min(4.0, length/4)
        if length:
            ux, uy = dx/length, dy/length
            masked_start = (x1+ux*inset, y1+uy*inset)
            masked_end = (x2-ux*inset, y2-uy*inset)
        else:
            masked_start, masked_end = start, end
        self.canvas.create_line(masked_start, masked_end, fill=PANEL, width=9,
                                capstyle="butt", tags="animated")

    def draw_resistor_between(self, start, end):
        """Piirtää IEC-tyylisen suorakulmaisen vastuksen pisteiden välille."""
        x1, y1 = start
        x2, y2 = end
        dx, dy = x2-x1, y2-y1
        length = math.hypot(dx, dy)
        if length <= 1e-9:
            return
        ux, uy = dx/length, dy/length
        px, py = -uy, ux
        self.mask_component_line(start, end)

        # Vastuksen runko vie keskimmäiset 64 prosenttia komponentin
        # kokonaispituudesta. Päihin jää lyhyet liitosjohtimet, joten
        # symboli liittyy aina katkeamatta ympäröivään johtimeen.
        half_body = 0.32 * length
        half_width = min(18.0, 0.18 * length)
        cx, cy = (x1+x2)/2, (y1+y2)/2
        body_start = (cx-ux*half_body, cy-uy*half_body)
        body_end = (cx+ux*half_body, cy+uy*half_body)
        corners = [
            (body_start[0]+px*half_width, body_start[1]+py*half_width),
            (body_end[0]+px*half_width, body_end[1]+py*half_width),
            (body_end[0]-px*half_width, body_end[1]-py*half_width),
            (body_start[0]-px*half_width, body_start[1]-py*half_width),
        ]
        self.canvas.create_line(start, body_start, fill=YELLOW, width=5,
                                capstyle="round", tags="animated")
        self.canvas.create_line(body_end, end, fill=YELLOW, width=5,
                                capstyle="round", tags="animated")
        self.canvas.create_polygon(corners, fill=PANEL, outline=YELLOW,
                                   width=5, joinstyle="round",
                                   tags="animated")

    def draw_thevenin_circuit(self, glow, width):
        """Piirtää kuvan viisi Thévenin-muunnoksen vaihetta."""
        kind = self.challenge.circuit_type
        _, series, branch, output = self.challenge.resistances
        shunt = self.challenge.resistances[0]
        top, bottom = 220, 450
        left, middle, port = 150, 400, 590

        full_circuit = kind in {"thevenin_voltage", "thevenin_short_current",
                                "thevenin_resistance"}
        if full_circuit:
            self.canvas.create_line(left, top, 240, top, fill=glow, width=width,
                                    tags="animated")
            self.canvas.create_line(360, top, middle, top, fill=glow, width=width,
                                    tags="animated")
            self.canvas.create_line(left, bottom, port, bottom, fill=glow, width=width,
                                    tags="animated")
            self.draw_horizontal_resistor(240, 360, top)
            self.canvas.create_line(middle, top, middle, 290, fill=glow,
                                    width=width, tags="animated")
            self.canvas.create_line(middle, 380, middle, bottom, fill=glow,
                                    width=width, tags="animated")
            self.draw_resistor(middle, 335)

            # Lähteen rinnakkaisvastus R1 on mukana alkuperäisessä piirissä.
            r0_x = 205
            self.canvas.create_line(r0_x, top, r0_x, 290, fill=glow,
                                    width=width, tags="animated")
            self.canvas.create_line(r0_x, 380, r0_x, bottom, fill=glow,
                                    width=width, tags="animated")
            self.draw_resistor(r0_x, 335)
            self.canvas.create_text(r0_x+28, 335, anchor="w", text=f"R1\n{shunt} Ω",
                                    fill=YELLOW, font=("Arial", 9, "bold"),
                                    tags="animated")

            if kind == "thevenin_resistance":
                # Riippumaton jännitelähde korvataan oikosululla.
                self.canvas.create_line(left, top, left, bottom, fill=glow,
                                        width=width, tags="animated")
            else:
                self.canvas.create_line(left, top, left, 300, fill=glow,
                                        width=width, tags="animated")
                self.canvas.create_line(left, 370, left, bottom, fill=glow,
                                        width=width, tags="animated")
                self.draw_battery(left, 335)
        else:
            # Kun lähde ja sen oikosuljettu rinnakkaishaara on poistettu,
            # R2 ja R3 näkyvät saman kahden solmun välisinä rinnakkaishaaroina.
            parallel_left = 245
            self.canvas.create_line(parallel_left, bottom, port, bottom, fill=glow,
                                    width=width, tags="animated")
            self.canvas.create_line(middle, top, middle, 290, fill=glow,
                                    width=width, tags="animated")
            self.canvas.create_line(middle, 380, middle, bottom, fill=glow,
                                    width=width, tags="animated")
            self.draw_resistor(middle, 335)
            if kind == "thevenin_parallel":
                # Kuvan vaihe (d): R2 on silmukan yläreunassa.
                self.canvas.create_line(parallel_left, top, 275, top, fill=glow,
                                        width=width, tags="animated")
                self.draw_horizontal_resistor(275, 365, top)
                self.canvas.create_line(365, top, middle, top, fill=glow,
                                        width=width, tags="animated")
                self.canvas.create_line(parallel_left, top, parallel_left, bottom,
                                        fill=glow, width=width, tags="animated")
            else:
                # Kuvan vaihe (e): R2 ja R3 piirretään vierekkäisiksi haaroiksi.
                self.canvas.create_line(parallel_left, top, middle, top, fill=glow,
                                        width=width, tags="animated")
                self.canvas.create_line(parallel_left, top, parallel_left, 290,
                                        fill=glow, width=width, tags="animated")
                self.canvas.create_line(parallel_left, 380, parallel_left, bottom,
                                        fill=glow, width=width, tags="animated")
                self.draw_resistor(parallel_left, 335)

        # R4 on aina sarjassa portin A kanssa.
        self.canvas.create_line(middle, top, 465, top, fill=glow, width=width,
                                tags="animated")
        self.draw_horizontal_resistor(465, 565, top)
        self.canvas.create_line(565, top, port, top, fill=glow, width=width,
                                tags="animated")
        self.canvas.create_text(515, 180, text=f"R4  {output} Ω", fill=YELLOW,
                                font=("Arial", 10, "bold"), tags="animated")

        if full_circuit:
            self.canvas.create_text(300, 180, text=f"R2  {series} Ω", fill=YELLOW,
                                    font=("Arial", 10, "bold"), tags="animated")
        else:
            if kind == "thevenin_parallel":
                self.canvas.create_text(320, 180, text=f"R2  {series} Ω",
                                        fill=YELLOW, font=("Arial", 10, "bold"),
                                        tags="animated")
            else:
                self.canvas.create_text(215, 335, anchor="e",
                                        text=f"R2\n{series} Ω", fill=YELLOW,
                                        font=("Arial", 9, "bold"), tags="animated")
        self.canvas.create_text(middle+28, 335, anchor="w", text=f"R3\n{branch} Ω",
                                fill=YELLOW, font=("Arial", 9, "bold"), tags="animated")
        self.canvas.create_text(port+14, top, anchor="w", text="A", fill=WHITE,
                                font=("Arial", 12, "bold"), tags="animated")
        self.canvas.create_text(port+14, bottom, anchor="w", text="B", fill=WHITE,
                                font=("Arial", 12, "bold"), tags="animated")
        for x, y in ((port, top), (port, bottom), (middle, top), (middle, bottom)):
            self.canvas.create_oval(x-6, y-6, x+6, y+6, fill=WHITE, outline=CYAN,
                                    width=2, tags="animated")

        if kind == "thevenin_short_current":
            self.canvas.create_line(port, top, port, bottom, fill=CYAN, width=5,
                                    arrow="last", tags="animated")
            self.canvas.create_text(port-18, 335, anchor="e", text="Isc",
                                    fill=WHITE, font=("Arial", 11, "bold"),
                                    tags="animated")

        # Vain lähteellisissä kaavioissa esitetään liikkuvaa varausta.
        if self.running and kind in {"thevenin_voltage", "thevenin_short_current"}:
            source_voltage = self.challenge.voltage
            i0 = source_voltage / shunt
            if kind == "thevenin_short_current":
                parallel_load = branch * output / (branch + output)
                node_voltage = (source_voltage * parallel_load
                                / (series + parallel_load))
                i2 = node_voltage / branch
                i3 = node_voltage / output
            else:
                node_voltage = source_voltage * branch / (series + branch)
                i2 = node_voltage / branch
                i3 = 0.0  # Avoimessa portissa R3:n läpi ei kulje virtaa.

            # Jokainen reitti on suljettu virtasilmukka. R2- ja R3-reitit
            # kulkevat yhteisen R1:n kautta, joten R1:llä näkyvä hiukkasmäärä
            # on automaattisesti haaravirtojen summa.
            current_routes = [
                (i0, [(left, bottom), (left, top), (r0_x, top),
                      (r0_x, bottom), (left, bottom)]),
                (i2, [(left, bottom), (left, top), (middle, top),
                      (middle, bottom), (left, bottom)]),
            ]
            if i3 > 0:
                current_routes.append(
                    (i3, [(left, bottom), (left, top), (middle, top),
                          (port, top), (port, bottom), (left, bottom)])
                )

            self.draw_closed_current_particles(current_routes)

    def draw_ac_network_circuit(self, glow, width):
        """Piirtää tehtävien 19–30 sarja-, rinnakkais- ja yhdistelmäpiirit."""
        kind = self.challenge.circuit_type
        if kind == "ac_complex":
            self.draw_complex_ac_circuit(glow, width)
            return

        top, bottom = 215, 455
        left, right = 140, 570
        self.canvas.create_line(left, top, left, bottom, fill=glow, width=width,
                                tags="animated")
        self.draw_ac_source(left, 335)

        parallel_kinds = {"ac_parallel_rc", "ac_parallel_rl",
                          "ac_parallel_rlc", "ac_parallel_lc"}
        components = []
        if kind in {"ac_resistive", "ac_series_rc", "ac_parallel_rc",
                    "ac_series_rlc", "ac_series_rl", "ac_parallel_rl",
                    "ac_parallel_rlc"}:
            components.append(("R", self.challenge.resistances[0]))
        if kind in {"ac_series_rlc", "ac_series_rl", "ac_parallel_rl",
                    "ac_parallel_rlc", "ac_inductive", "ac_series_lc",
                    "ac_parallel_lc"}:
            components.append(("L", self.challenge.inductance))
        if kind in {"ac_series_rc", "ac_parallel_rc", "ac_series_rlc",
                    "ac_capacitive", "ac_parallel_rlc", "ac_series_lc",
                    "ac_parallel_lc"}:
            components.append(("C", self.challenge.capacitances[0]))

        if kind in parallel_kinds:
            positions = ({2: [330, 480], 3: [280, 410, 540]}[len(components)])
            # Rinnakkaispiirin yhteiset johtimet päättyvät viimeiseen haaraan.
            # Oikealle ei jätetä avoimeksi näyttäviä johdinjatkeita.
            branch_end = positions[-1]
            self.canvas.create_line(left, top, branch_end, top, fill=glow,
                                    width=width, tags="animated")
            self.canvas.create_line(left, bottom, branch_end, bottom,
                                    fill=glow, width=width, tags="animated")
            branch_currents = []
            angular = 2 * math.pi * self.challenge.frequency
            for x, (component, value) in zip(positions, components):
                self.canvas.create_line(x, top, x, 275, fill=glow,
                                        width=width, tags="animated")
                self.canvas.create_line(x, 395, x, bottom, fill=glow,
                                        width=width, tags="animated")
                if component == "R":
                    self.draw_resistor(x, 335)
                    branch_impedance = complex(value, 0)
                    label = f"R {value:g} Ω"
                elif component == "L":
                    self.draw_vertical_inductor(x, 335)
                    branch_impedance = 1j*angular*value
                    label = f"L {value:g} H"
                else:
                    self.draw_capacitor(x, 335)
                    branch_impedance = 1/(1j*angular*value)
                    label = f"C {value*1e6:g} µF"
                branch_currents.append(self.challenge.voltage/branch_impedance)
            if self.running:
                routes = [
                    (current, [(left, bottom), (left, top), (x, top),
                               (x, bottom), (left, bottom)])
                    for current, x in zip(branch_currents, positions)
                ]
                self.draw_ac_phasor_particles(routes)
        else:
            # Sarjapiirissä sama virta kulkee kaikkien komponenttien läpi.
            self.canvas.create_line(left, bottom, right, bottom, fill=glow,
                                    width=width, tags="animated")
            component_width = 90
            gap = 18
            total_width = len(components)*component_width + (len(components)-1)*gap
            start = 355-total_width/2
            self.canvas.create_line(left, top, start, top, fill=glow,
                                    width=width, tags="animated")
            cursor = start
            for component_index, (component, value) in enumerate(components):
                if component_index:
                    # Sarjakomponenttien valiin varattu tila on johdinta,
                    # ei avointa katkoa.
                    self.canvas.create_line(cursor-gap, top, cursor, top,
                                            fill=glow, width=width,
                                            tags="animated")
                end = cursor+component_width
                if component == "R":
                    self.draw_horizontal_resistor(cursor, end, top)
                    label = f"R {value:g} Ω"
                elif component == "L":
                    self.draw_horizontal_inductor_simple(cursor, end, top)
                    label = f"L {value:g} H"
                else:
                    self.draw_horizontal_capacitor(cursor, end, top)
                    label = f"C {value*1e6:g} µF"
                self.canvas.create_text((cursor+end)/2, 170, text=label,
                                        fill=YELLOW,
                                        font=("Arial", 9, "bold"),
                                        tags="animated")
                cursor = end+gap
            self.canvas.create_line(cursor-gap, top, right, top, right, bottom,
                                    fill=glow, width=width, tags="animated")
            if self.running:
                self.draw_closed_current_particles([
                    (self.challenge.current,
                     [(left, bottom), (left, top), (right, top),
                      (right, bottom), (left, bottom)])
                ], minimum=5)

    def draw_complex_ac_circuit(self, glow, width):
        """Piirtää tehtävän 30 yhdistetyn sarja–rinnakkaisen RLC-verkon."""
        r1, r2, r3 = self.challenge.resistances
        c1, c2, c3 = self.challenge.capacitances
        top, bottom = 215, 455
        source_x, node_a, node_b, right = 120, 350, 485, 590

        self.canvas.create_line(source_x, top, 185, top, fill=glow,
                                width=width, tags="animated")
        self.draw_horizontal_resistor(185, 265, top)
        self.draw_horizontal_inductor_simple(265, node_a, top)
        self.canvas.create_line(source_x, top, source_x, bottom,
                                fill=glow, width=width, tags="animated")
        self.draw_ac_source(source_x, 335)

        # C1 on ensimmäinen paluuhaara. Toinen haara sisältää C2:n ja
        # rinnakkaiset R2/L2-komponentit.
        self.canvas.create_line(node_a, top, node_a, 290, fill=glow,
                                width=width, tags="animated")
        self.canvas.create_line(node_a, 380, node_a, bottom, fill=glow,
                                width=width, tags="animated")
        self.draw_capacitor(node_a, 335)
        self.draw_horizontal_capacitor(node_a, node_b, top)
        self.canvas.create_line(node_b, top, right, top,
                                fill=glow, width=width, tags="animated")
        for x, component in ((node_b, "R"), (right, "L")):
            self.canvas.create_line(x, top, x, 275, fill=glow, width=width,
                                    tags="animated")
            self.canvas.create_line(x, 385, x, 395, fill=glow, width=width,
                                    tags="animated")
            if component == "R":
                self.draw_resistor(x, 330)
            else:
                self.draw_vertical_inductor(x, 330)
        self.canvas.create_line(node_b, 395, right, 395,
                                fill=glow, width=width, tags="animated")

        self.canvas.create_line(node_a, bottom, 300, bottom, fill=glow,
                                width=width, tags="animated")
        self.draw_horizontal_resistor(220, 300, bottom)
        self.draw_horizontal_capacitor(140, 220, bottom)
        self.canvas.create_line(source_x, bottom, 140, bottom, fill=glow,
                                width=width, tags="animated")
        self.canvas.create_line(right, 395, right, bottom, node_a, bottom,
                                fill=glow, width=width, tags="animated")

        labels = [
            (225, 170, f"R1 {r1} Ω"), (305, 170,
             f"L1 {self.challenge.inductance:g} H"),
            (320, 290, f"C1 {c1*1e6:g} µF"),
            (418, 170, f"C2 {c2*1e6:g} µF"),
            (455, 330, f"R2 {r2} Ω"),
            (630, 330, f"L2 {self.challenge.secondary_inductance:g} H"),
            (260, 495, f"R3 {r3} Ω"), (180, 495, f"C3 {c3*1e6:g} µF"),
        ]
        for x, y, label in labels:
            self.canvas.create_text(x, y, text=label, fill=YELLOW,
                                    font=("Arial", 8, "bold"),
                                    tags="animated")
        if self.running:
            angular = 2*math.pi*self.challenge.frequency
            zc1 = 1/(1j*angular*c1)
            zc2 = 1/(1j*angular*c2)
            zl2 = 1j*angular*self.challenge.secondary_inductance
            zr2 = complex(r2, 0)
            zinner = 1/(1/zr2 + 1/zl2)
            branch_b = zc2 + zinner
            middle = 1/(1/zc1 + 1/branch_b)
            total_current = self.challenge.voltage/self.challenge.complex_impedance
            middle_voltage = total_current*middle
            c1_current = middle_voltage/zc1
            branch_b_current = middle_voltage/branch_b
            inner_voltage = branch_b_current*zinner
            r2_current = inner_voltage/zr2
            l2_current = inner_voltage/zl2
            routes = [
                (c1_current,
                 [(source_x, bottom), (source_x, top), (node_a, top),
                  (node_a, bottom), (source_x, bottom)]),
                (r2_current,
                 [(source_x, bottom), (source_x, top), (node_a, top),
                  (node_b, top), (node_b, 395), (right, 395),
                  (right, bottom), (node_a, bottom),
                  (source_x, bottom)]),
                (l2_current,
                 [(source_x, bottom), (source_x, top), (node_a, top),
                  (right, top), (right, 395), (right, bottom),
                  (node_a, bottom),
                  (source_x, bottom)]),
            ]
            self.draw_ac_phasor_particles(routes)

    def draw_horizontal_inductor_simple(self, x1, x2, y):
        """Piirtää vaakasuuntaisen käämin ilman kiinteään paikkaan sidottua tekstiä."""
        self.mask_component_line((x1, y), (x2, y))
        points = [(x1, y)]
        for step in range(61):
            ratio = step/60
            points.append((x1+(x2-x1)*ratio,
                           y-15*math.sin(ratio*5*2*math.pi)))
        self.canvas.create_line(points, fill=YELLOW, width=5, smooth=True,
                                tags="animated")

    def draw_three_source_mesh_circuit(self, glow, width):
        """Piirtää kolme rinnakkaista, eri lähteitä sisältävää haaraa."""
        top_node, bottom_node = (365, 205), (365, 465)
        left_x, right_x = 165, 570
        e1, e2, e3 = self.challenge.voltages
        r1, r2, r3, r4, r5 = self.challenge.resistances

        # Vasen haara: R3, R2, E1 ja R1 sarjassa.
        self.canvas.create_line(top_node, 325, 205, fill=glow, width=width,
                                tags="animated")
        self.draw_horizontal_resistor(205, 325, 205)
        self.canvas.create_line(205, 205, left_x, 205,
                                fill=glow, width=width, tags="animated")
        self.canvas.create_line(left_x, 205, left_x, 285,
                                fill=glow, width=width, tags="animated")
        self.canvas.create_line(left_x, 375, left_x, 465,
                                fill=glow, width=width, tags="animated")
        self.draw_resistor(left_x, 330)
        self.canvas.create_line(left_x, 465, 205, 465,
                                fill=glow, width=width, tags="animated")
        self.draw_horizontal_voltage_source(205, 255, 465, positive_left=True)
        self.draw_horizontal_resistor(255, 345, 465)
        self.canvas.create_line(345, 465, bottom_node,
                                fill=glow, width=width, tags="animated")

        # Keskimmäinen haara: E3 ja R5.
        self.canvas.create_line(365, 205, 365, 245, fill=glow, width=width,
                                tags="animated")
        self.draw_vertical_voltage_source(365, 270, positive_top=True)
        self.canvas.create_line(365, 295, 365, 345, fill=glow, width=width,
                                tags="animated")
        self.draw_resistor(365, 390)
        self.canvas.create_line(365, 435, 365, 465, fill=glow, width=width,
                                tags="animated")

        # Oikea haara: R4 ja vastakkaiseen suuntaan vaikuttava E2.
        self.canvas.create_line(top_node, 410, 205, fill=glow, width=width,
                                tags="animated")
        self.draw_horizontal_resistor(410, 530, 205)
        self.canvas.create_line(530, 205, right_x, 205, right_x, 465,
                                fill=glow, width=width, tags="animated")
        self.draw_horizontal_voltage_source(470, 520, 465, positive_left=True)
        self.canvas.create_line(bottom_node, 470, 465, fill=glow, width=width,
                                tags="animated")
        self.canvas.create_line(520, 465, right_x, 465, fill=glow, width=width,
                                tags="animated")

        labels = [
            (265, 165, f"R3 {r3} Ω"), (125, 330, f"R2 {r2} Ω"),
            (300, 425, f"R1 {r1} Ω"), (470, 165, f"R4 {r4} Ω"),
            (405, 390, f"R5 {r5} Ω"), (225, 505, f"E1 {e1} V"),
            (405, 270, f"E3 {e3} V"), (500, 505, f"E2 {e2} V"),
        ]
        for x, y, label in labels:
            self.canvas.create_text(x, y, text=label, fill=YELLOW,
                                    font=("Arial", 9, "bold"),
                                    tags="animated")
        self.canvas.create_text(135, 390, text="I1", fill=WHITE,
                                font=("Arial", 10, "bold"), tags="animated")
        self.canvas.create_text(390, 335, text="I2", fill=WHITE,
                                font=("Arial", 10, "bold"), tags="animated")
        self.canvas.create_text(595, 335, text="I3", fill=WHITE,
                                font=("Arial", 10, "bold"), tags="animated")

        for point in (top_node, bottom_node):
            x, y = point
            self.canvas.create_oval(x-7, y-7, x+7, y+7, fill=WHITE,
                                    outline=CYAN, width=2, tags="animated")

        if self.running:
            currents = self.challenge.expected_values
            routes = [
                [top_node, (left_x, 205), (left_x, 465), bottom_node],
                [top_node, bottom_node],
                [top_node, (right_x, 205), (right_x, 465), bottom_node],
            ]
            largest = max(abs(current) for current in currents)
            flow = (self.branch_flow / 180) % 1
            for branch_index, (current, route) in enumerate(zip(currents, routes)):
                if current < 0:
                    route = list(reversed(route))
                count = self.relative_particle_count(abs(current), largest,
                                                     route, minimum=2)
                for index in range(count):
                    x, y = self.polyline_point(
                        route, flow + index/count + branch_index*0.04
                    )
                    self.canvas.create_oval(x-5, y-5, x+5, y+5,
                                            fill=WHITE, outline=CYAN, width=2,
                                            tags="animated")

    def draw_horizontal_voltage_source(self, x1, x2, y, positive_left=True):
        """Piirtää vaakahaaraan standardin paristosymbolin."""
        self.mask_component_line((x1, y), (x2, y))
        middle = (x1+x2)/2
        long_x = middle-7 if positive_left else middle+7
        short_x = middle+7 if positive_left else middle-7
        self.canvas.create_line(x1, y, min(long_x, short_x), y, fill=YELLOW,
                                width=4, tags="animated")
        self.canvas.create_line(long_x, y-25, long_x, y+25,
                                fill=YELLOW, width=5, tags="animated")
        self.canvas.create_line(short_x, y-15, short_x, y+15,
                                fill=YELLOW, width=5, tags="animated")
        self.canvas.create_line(max(long_x, short_x), y, x2, y,
                                fill=YELLOW, width=4,
                                tags="animated")

    def draw_vertical_voltage_source(self, x, y, positive_top=True):
        """Piirtää pystyhaaraan standardin paristosymbolin."""
        self.mask_component_line((x, y-35), (x, y+35))
        long_y = y-7 if positive_top else y+7
        short_y = y+7 if positive_top else y-7
        self.canvas.create_line(x, y-35, x, min(long_y, short_y),
                                fill=YELLOW, width=4, tags="animated")
        self.canvas.create_line(x-25, long_y, x+25, long_y,
                                fill=YELLOW, width=5, tags="animated")
        self.canvas.create_line(x-15, short_y, x+15, short_y,
                                fill=YELLOW, width=5, tags="animated")
        self.canvas.create_line(x, max(long_y, short_y), x, y+35,
                                fill=YELLOW, width=4, tags="animated")

    def draw_lc_oscillator_circuit(self, glow, width):
        """Piirtää operaatiovahvistimella ylläpidetyn LC-oskillaattorin."""
        left_node, right_node = (250, 375), (510, 375)
        output = (510, 235)
        bottom = 500
        c1, c2 = (value * 1e9 for value in self.challenge.capacitances)
        resistance = self.challenge.resistances[0]

        # Operaatiovahvistin ja sen tulot.
        self.canvas.create_polygon(155, 165, 155, 305, 320, 235,
                                   outline=YELLOW, fill="", width=4,
                                   tags="animated")
        self.canvas.create_text(185, 205, text="+", fill=WHITE,
                                font=("Arial", 18, "bold"), tags="animated")
        self.canvas.create_text(185, 267, text="−", fill=WHITE,
                                font=("Arial", 18, "bold"), tags="animated")
        self.canvas.create_text(235, 235, text="A", fill=YELLOW,
                                font=("Arial", 17, "bold"), tags="animated")
        self.canvas.create_line(320, 235, output, fill=glow, width=width,
                                tags="animated")

        # Positiivinen tulo seuraa vasenta LC-solmua. Negatiivinen tulo on
        # maadoitettu kuvan mukaisesti.
        self.canvas.create_line(155, 200, 115, 200, 115, left_node[1],
                                left_node, fill=glow, width=width,
                                tags="animated")
        self.canvas.create_line(155, 270, 135, 270, 135, 305,
                                fill=glow, width=width, tags="animated")
        self.draw_ground(135, 305)

        # Ulostulon R1, solmujen välinen L sekä maahan kytketyt C1 ja C2.
        self.canvas.create_line(output, right_node, fill=glow, width=width,
                                tags="animated")
        self.draw_resistor(510, 305)
        self.canvas.create_text(545, 305,
                                text=f"R1\n{resistance/1000:g} kΩ",
                                anchor="w", fill=YELLOW,
                                font=("Arial", 9, "bold"), tags="animated")

        coil_points = [left_node]
        self.mask_component_line(left_node, right_node)
        for step in range(61):
            ratio = step / 60
            x = left_node[0] + (right_node[0]-left_node[0]) * ratio
            y = left_node[1] - 16 * math.sin(ratio * 6 * 2 * math.pi)
            coil_points.append((x, y))
        self.canvas.create_line(coil_points, fill=YELLOW, width=5,
                                smooth=True, tags="animated")
        self.canvas.create_text(380, 340,
                                text=f"L  {self.challenge.inductance*1e3:g} mH",
                                fill=YELLOW, font=("Arial", 10, "bold"),
                                tags="animated")

        for x, value, name in ((left_node[0], c1, "C1"),
                               (right_node[0], c2, "C2")):
            self.canvas.create_line(x, left_node[1], x, bottom,
                                    fill=glow, width=width, tags="animated")
            self.draw_capacitor(x, 440)
            self.draw_ground(x, bottom)
            self.canvas.create_text(x+34, 440, anchor="w",
                                    text=f"{name}\n{value:g} nF",
                                    fill=YELLOW, font=("Arial", 9, "bold"),
                                    tags="animated")

        for x, y in (left_node, right_node, output):
            self.canvas.create_oval(x-6, y-6, x+6, y+6, fill=WHITE,
                                    outline=CYAN, width=2, tags="animated")

        if self.running:
            oscillation = math.sin(self.phase * 2)
            # Käämin ja vahvistimen syöttöhaaran varaukset värähtelevät
            # edestakaisin; kondensaattorien eristeen läpi ei kuljeta.
            paths = [
                [(320, 235), output, right_node],
                [right_node, left_node],
            ]
            for path_index, path in enumerate(paths):
                count = self.relative_particle_count(1.0, 1.0, path, minimum=3)
                for index in range(count):
                    position = 0.5 + 0.16*oscillation + index/count
                    x, y = self.polyline_point(path,
                                               position + path_index*0.08)
                    self.canvas.create_oval(x-5, y-5, x+5, y+5,
                                            fill=WHITE, outline=CYAN, width=2,
                                            tags="animated")
            for capacitor_index, x in enumerate((left_node[0], right_node[0])):
                motion = 14 * math.sin(self.phase*2 + capacitor_index*math.pi)
                for y in (405+motion, 475-motion):
                    self.canvas.create_oval(x-5, y-5, x+5, y+5,
                                            fill=WHITE, outline=CYAN, width=2,
                                            tags="animated")

    def draw_ground(self, x, y):
        """Piirtää maadoitussymbolin annetun pisteen alapuolelle."""
        self.canvas.create_line(x, y, x, y+8, fill=YELLOW, width=3,
                                tags="animated")
        self.canvas.create_line(x-16, y+8, x+16, y+8, fill=YELLOW, width=3,
                                tags="animated")
        self.canvas.create_line(x-11, y+14, x+11, y+14, fill=YELLOW, width=3,
                                tags="animated")
        self.canvas.create_line(x-6, y+20, x+6, y+20, fill=YELLOW, width=3,
                                tags="animated")

    def draw_coupled_lc_circuit(self, glow, width):
        """Piirtää kaksi Cg-kondensaattorilla kytkettyä rinnakkaista LC-piiriä."""
        top, bottom = 220, 450
        left_node, right_node = 315, 405
        l1_x, c1_x = 155, 270
        l2_x, c2_x, source_x = 445, 525, 605

        # Yhteinen alajohdin ja kaksi erillistä ylänapaa. Cg on ainoa
        # sähköinen yhteys ylänapojen välillä.
        self.canvas.create_line(l1_x, bottom, source_x, bottom, fill=glow,
                                width=width, tags="animated")
        self.canvas.create_line(l1_x, top, left_node, top, fill=glow,
                                width=width, tags="animated")
        self.canvas.create_line(right_node, top, source_x, top, fill=glow,
                                width=width, tags="animated")
        self.draw_horizontal_capacitor(left_node, right_node, top)

        for x in (l1_x, c1_x, l2_x, c2_x):
            self.canvas.create_line(x, top, x, bottom, fill=glow,
                                    width=width, tags="animated")
        self.draw_vertical_inductor(l1_x, 335)
        self.draw_capacitor(c1_x, 335)
        self.draw_vertical_inductor(l2_x, 335)
        self.draw_capacitor(c2_x, 335)
        self.canvas.create_line(source_x, top, source_x, bottom, fill=glow,
                                width=width, tags="animated")
        self.draw_ac_source(source_x, 335)

        c1, c2 = (value * 1e6 for value in self.challenge.capacitances)
        cg = self.challenge.coupling_capacitance * 1e6
        labels = [
            (l1_x-28, 270, f"L1\n{self.challenge.inductance:g} H"),
            (c1_x-28, 270, f"C1\n{c1:g} µF"),
            (l2_x-28, 270, f"L2\n{self.challenge.secondary_inductance:g} H"),
            (c2_x-28, 270, f"C2\n{c2:g} µF"),
            ((left_node + right_node) / 2, 185, f"Cg  {cg:g} µF"),
        ]
        for x, y, label in labels:
            self.canvas.create_text(x, y, text=label, fill=YELLOW,
                                    font=("Arial", 9, "bold"), tags="animated")

        # Vaihtovirralla varaukset värähtelevät edestakaisin. Kondensaattorin
        # eristeen läpi ei piirretä hiukkasia kulkemaan.
        if self.running:
            oscillation = math.sin(self.phase * 2)
            angular_frequency = 2 * math.pi * self.challenge.frequency
            c1_value, c2_value = self.challenge.capacitances
            left_admittance = 1j * (
                angular_frequency*c1_value
                - 1/(angular_frequency*self.challenge.inductance)
            )
            left_impedance = (1/left_admittance if abs(left_admittance) > 1e-12
                              else complex(0, 1e12))
            coupling_impedance = 1/(1j*angular_frequency
                                    * self.challenge.coupling_capacitance)
            coupling_current = (self.challenge.voltage
                                / abs(coupling_impedance + left_impedance))
            left_voltage = coupling_current * abs(left_impedance)
            inductor_currents = [
                self.challenge.voltage
                / (angular_frequency*self.challenge.secondary_inductance),
                left_voltage / (angular_frequency*self.challenge.inductance),
            ]
            capacitor_currents = [
                left_voltage * angular_frequency * c1_value,
                self.challenge.voltage * angular_frequency * c2_value,
                coupling_current,
            ]
            routes = [
                (inductor_currents[0],
                 [(source_x, bottom), (l2_x, bottom), (l2_x, top),
                  (source_x, top)]),
                (inductor_currents[1],
                 [(c1_x, bottom), (l1_x, bottom), (l1_x, top),
                  (c1_x, top)]),
            ]
            largest_component_current = max(inductor_currents + capacitor_currents)
            for route_index, (current, route) in enumerate(routes):
                count = self.relative_particle_count(
                    current, largest_component_current, route, minimum=2
                )
                for index in range(count):
                    position = 0.5 + 0.18 * oscillation + index / count
                    x, y = self.polyline_point(route, position + route_index * 0.06)
                    self.canvas.create_oval(x-5, y-5, x+5, y+5, fill=WHITE,
                                            outline=CYAN, width=2, tags="animated")

            # Kondensaattorien johdinelektronit värähtelevät levyjä kohti;
            # pallot eivät ylitä eristettä. Määrä suhteutetaan samaan
            # komponenttivirtojen maksimiin kuin käämien pallot.
            for capacitor_index, (x, current) in enumerate(
                    ((c1_x, capacitor_currents[0]),
                     (c2_x, capacitor_currents[1]))):
                density_route = [(x, 245), (x, 425)]
                count = self.relative_particle_count(
                    current, largest_component_current, density_route, minimum=2
                )
                motion = 15 * math.sin(self.phase*2 + capacitor_index*.4)
                for index in range(count):
                    spread = (index-(count-1)/2) * 9
                    for y in (295+motion+spread, 375-motion-spread):
                        self.canvas.create_oval(x-5, y-5, x+5, y+5,
                                                fill=WHITE, outline=CYAN,
                                                width=2, tags="animated")

            cg_count = self.relative_particle_count(
                capacitor_currents[2], largest_component_current,
                [(left_node, top), (right_node, top)], minimum=2,
            )
            cg_motion = 10 * math.sin(self.phase*2)
            for index in range(cg_count):
                spread = (index-(cg_count-1)/2) * 8
                for x in (left_node+15+cg_motion+spread,
                          right_node-15-cg_motion-spread):
                    self.canvas.create_oval(x-5, top-5, x+5, top+5,
                                            fill=WHITE, outline=CYAN,
                                            width=2, tags="animated")

        for particle in self.particles:
            x, y, _, _, life, color = particle
            radius = max(2, life / 10)
            self.canvas.create_oval(x-radius, y-radius, x+radius, y+radius,
                                    fill=color, outline="", tags="animated")

    def draw_horizontal_capacitor(self, x1, x2, y):
        """Piirtää vaakajohtimessa olevan kondensaattorin."""
        self.mask_component_line((x1, y), (x2, y))
        middle = (x1 + x2) / 2
        self.canvas.create_line(x1, y, middle-9, y, fill=YELLOW, width=5,
                                tags="animated")
        self.canvas.create_line(middle-9, y-25, middle-9, y+25,
                                fill=YELLOW, width=6, tags="animated")
        self.canvas.create_line(middle+9, y-25, middle+9, y+25,
                                fill=YELLOW, width=6, tags="animated")
        self.canvas.create_line(middle+9, y, x2, y, fill=YELLOW, width=5,
                                tags="animated")

    def draw_vertical_inductor(self, x, y):
        """Piirtää pystysuuntaisen käämin LC-haaraan."""
        self.mask_component_line((x, y-60), (x, y+60))
        self.canvas.create_line(x, y-60, x, y-55, fill=YELLOW, width=5,
                                tags="animated")
        points = [(x, y-55)]
        for step in range(61):
            ratio = step / 60
            coil_y = y - 55 + 110 * ratio
            coil_x = x + 14 * math.sin(ratio * 5 * 2 * math.pi)
            points.append((coil_x, coil_y))
        self.canvas.create_line(points, fill=YELLOW, width=5, smooth=True,
                                tags="animated")
        self.canvas.create_line(x, y+55, x, y+60, fill=YELLOW, width=5,
                                tags="animated")

    @staticmethod
    def parallel_positions(component, count):
        """Palauttaa symmetriset haarapaikat yhteisen liitosjohdon ympäriltä."""
        if component == "source":
            return [80, 180]
        if count == 2:
            return [515, 625]
        # Kolme vastusta tasavälein: R2 on pääjohdon kohdalla keskellä.
        return [515, 570, 625]

    def draw_resistor(self, x, y):
        """Piirtää pystysuuntaisen suorakulmaisen vastuksen."""
        self.draw_resistor_between((x, y-60), (x, y+60))

    def draw_horizontal_resistor(self, x1, x2, y):
        """Piirtää vaakasuuntaisen suorakulmaisen vastuksen."""
        self.draw_resistor_between((x1, y), (x2, y))

    def draw_capacitor(self, x, y):
        """Piirtää pystysuuntaisen kondensaattorin johtimen haaralle."""
        # Liitosjohdot ulottuvat rinnakkaishaarojen johtoihin (y +/- 60).
        # Aiempi +/-45 jätti kummallekin puolelle näkyvän 15 px katkoksen.
        self.mask_component_line((x, y-60), (x, y+60))
        self.canvas.create_line(x, y-60, x, y-9, fill=YELLOW, width=5,
                                tags="animated")
        self.canvas.create_line(x-25, y-9, x+25, y-9, fill=YELLOW, width=6,
                                tags="animated")
        self.canvas.create_line(x-25, y+9, x+25, y+9, fill=YELLOW, width=6,
                                tags="animated")
        self.canvas.create_line(x, y+9, x, y+60, fill=YELLOW, width=5,
                                tags="animated")

    def draw_inductor(self, x1, x2, y):
        """Piirtää vaakasuuntaisen käämin ja animoidun magneettikentän."""
        self.mask_component_line((x1, y), (x2, y))
        coil_points = [(x1, y)]
        turns = 5
        samples = 60
        for step in range(samples + 1):
            ratio = step / samples
            x = x1 + (x2 - x1) * ratio
            coil_y = y - 17 * math.sin(ratio * turns * 2 * math.pi)
            coil_points.append((x, coil_y))
        self.canvas.create_line(coil_points, fill=YELLOW, width=5, smooth=True,
                                tags="animated")
        pulse = 3 * math.sin(self.phase * 3)
        for radius in (28, 38):
            self.canvas.create_arc((370-radius-pulse, y-radius, 370+radius+pulse, y+radius),
                                   start=200, extent=140, style="arc", outline=CYAN,
                                   width=2, tags="animated")
        self.canvas.create_text(370, 255, text="KÄÄMI", fill=MUTED,
                                font=("Arial", 11, "bold"), tags="animated")

    def animate(self):
        self.phase += 0.05
        speed = 0.003 + min(self.challenge.current, 5) * 0.0015
        if self.running:
            # Tasavirralla suunta on vakio. Vaihtovirralla hetkellinen suunta
            # vaihtuu sinimuotoisesti ja nopeus käy nollassa suunnanvaihdossa.
            flow_direction = (math.cos(self.phase * 2)
                              if self.challenge.frequency else 1.0)
            signed_speed = speed * flow_direction
            self.electrons = [(t + signed_speed) % 1 for t in self.electrons]
            self.branch_flow = (self.branch_flow + signed_speed * 210) % 180

        alive = []
        for p in self.particles:
            p[0] += p[2]
            p[1] += p[3]
            p[3] += 0.12
            p[4] -= 1
            if p[4] > 0:
                alive.append(p)
        self.particles = alive

        self.draw_circuit()
        self.canvas.itemconfigure(self.score_text,
                                  text=f"PISTEET {self.score}   •   TEHTÄVÄ {self.question_number}")
        self.canvas.itemconfigure(self.message_text, text=self.message,
                                  fill=self.message_color)

        if self.flash:
            color = GREEN if self.flash > 0 else RED
            self.canvas.configure(bg=color if abs(self.flash) % 4 < 2 else BG)
            self.flash += -1 if self.flash > 0 else 1
        else:
            self.canvas.configure(bg=BG)

        self.root.after(33, self.animate)


if __name__ == "__main__":
    app_root = tk.Tk()
    ElectricityGame(app_root)
    app_root.mainloop()
