import litex.regon as regon
import lxml.etree
import tkinter as tk
from tkinter import messagebox, scrolledtext, filedialog
from datetime import date
from fpdf import FPDF
import os

# --- Konfiguracja i funkcje PDF ---

class PDF(FPDF):
    def header(self):
        self.set_font('DejaVuSansCondensed', 'B', 12)
        self.cell(0, 10, 'Raport Danych REGON', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('DejaVuSansCondensed', 'I', 8)
        self.cell(0, 10, f'Strona {self.page_no()}/{{nb}}', 0, 0, 'C')

def get_current_date():
    return date.today().strftime("%d-%m-%Y")

def export_to_pdf_from_widget(content, initial_filename_prefix):
    if not content.strip():
        messagebox.showwarning("Błąd", "Brak danych do wyeksportowania do PDF.")
        return

    file_path = filedialog.asksaveasfilename(
        defaultextension=".pdf",
        filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        initialfile=f"{initial_filename_prefix}_{get_current_date()}.pdf"
    )

    if file_path:
        pdf = PDF()
        pdf.alias_nb_pages()
        try:
            pdf.add_font('DejaVuSansCondensed', '', 'DejaVuSansCondensed.ttf')
            pdf.add_font('DejaVuSansCondensed', 'B', 'DejaVuSansCondensed.ttf')
            pdf.add_font('DejaVuSansCondensed', 'I', 'DejaVuSansCondensed.ttf')
            pdf.set_font('DejaVuSansCondensed', '', 10)
        except RuntimeError as e:
            messagebox.showerror("Błąd czcionki", f"Nie można załadować czcionki DejaVuSansCondensed.ttf. Upewnij się, że plik jest w tym samym katalogu co skrypt: {e}")
            return
        
        pdf.add_page()
        
        for line in content.split('\n'):
            pdf.cell(0, 7, line, 0, 1, 'L')
        
        try:
            pdf.output(file_path)
            messagebox.showinfo("Sukces", f"Raport zapisano do: {file_path}")
        except Exception as e:
            messagebox.showerror("Błąd zapisu PDF", f"Nie udało się zapisać pliku PDF: {e}")

# --- Funkcje pobierania danych GUS ---

def pobierz_dane_gus_gui(nip):
    klucz_uzytkownika = "abcde12345abcde12345"
    klient = None
    dane_do_raportu = {}

    try:
        service_url = "https://wyszukiwarkaregontest.stat.gov.pl/wsBIR/UslugaBIRzewnPubl.svc"
        klient = regon.REGONAPI(service_url)
        klient.login(klucz_uzytkownika)

        wynik_wyszukiwania = klient.search(nip=nip, detailed=True)
        if not wynik_wyszukiwania:
            messagebox.showwarning("Brak danych", f"Nie znaleziono podmiotu dla NIPu: {nip}")
            return None

        glowny_element_odpowiedzi = wynik_wyszukiwania[0]
        
        dane_do_raportu['Regon'] = getattr(glowny_element_odpowiedzi, 'Regon', None)
        dane_do_raportu['Typ'] = getattr(glowny_element_odpowiedzi, 'Typ', None)
        dane_do_raportu['Nazwa'] = getattr(glowny_element_odpowiedzi, 'Nazwa', None)
        dane_do_raportu['Wojewodztwo'] = getattr(glowny_element_odpowiedzi, 'Wojewodztwo', None)
        dane_do_raportu['Powiat'] = getattr(glowny_element_odpowiedzi, 'Powiat', None)
        dane_do_raportu['Gmina'] = getattr(glowny_element_odpowiedzi, 'Gmina', None)
        dane_do_raportu['KodPocztowy'] = getattr(glowny_element_odpowiedzi, 'KodPocztowy', None)
        dane_do_raportu['Miejscowosc'] = getattr(glowny_element_odpowiedzi, 'Miejscowosc', None)
        dane_do_raportu['Ulica'] = getattr(glowny_element_odpowiedzi, 'Ulica', None)
        dane_do_raportu['Numer Nieruchomości'] = getattr(glowny_element_odpowiedzi, 'NrNieruchomosci', None)
        
        detailed_element = getattr(glowny_element_odpowiedzi, 'detailed', None)
        if detailed_element is not None:
            raw_data_zakonczenia_element = getattr(detailed_element, 'praw_dataZakonczeniaDzialalnosci', None)
            data_zakonczenia_text = raw_data_zakonczenia_element.text if raw_data_zakonczenia_element is not None else None

            if data_zakonczenia_text and data_zakonczenia_text.strip():
                dane_do_raportu['Informacja o skreśleniu z REGON'] = f"Działalność zakończona: {data_zakonczenia_text.strip()}"
            else:
                dane_do_raportu['Informacja o skreśleniu z REGON'] = "----------"
        else:
            dane_do_raportu['Informacja o skreśleniu z REGON'] = "----------"
        
        return dane_do_raportu

    except Exception as e:
        messagebox.showerror("Błąd", f"Wystąpił błąd: {e}")
        return None

    finally:
        try:
            if klient:
                klient.logout()
        except Exception:
            pass

# --- Funkcje obsługi historii ---

HISTORY_FILE = "historia_regon.txt"
search_history = []

def save_history():
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        for entry in search_history:
            f.write(entry + "\n")

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                search_history.append(line.strip())
        update_history_display()

def update_history_display():
    history_text.config(state=tk.NORMAL)
    history_text.delete(1.0, tk.END)
    for entry in reversed(search_history):
        history_text.insert(tk.END, entry + "\n")
    history_text.config(state=tk.DISABLED)

# --- Funkcje obsługi GUI i zdarzeń ---

drag_data = {'text': None}
is_uppercase = False
original_data = {}

def on_drag_start(event, source_entry):
    label_text = entry_labels[source_entry]
    value = source_entry.get()

    if is_uppercase:
        drag_data['text'] = f"{label_text.upper()}: {value.upper()}"
    else:
        drag_data['text'] = f"{label_text}: {value}"

    root.config(cursor="hand2")
    root.bind('<ButtonRelease-1>', on_drop_global)
    root.bind('<Motion>', on_drag_motion_global)

def on_drag_motion_global(event):
    pass

def on_drop_global(event):
    root.config(cursor="arrow")
    
    if drag_data['text']:
        x_root, y_root = event.x_root, event.y_root
        widget = root.winfo_containing(x_root, y_root)
        
        if widget and widget == selected_data_text:
            x_rel = x_root - selected_data_text.winfo_rootx()
            y_rel = y_root - selected_data_text.winfo_rooty()
            
            try:
                index = selected_data_text.index(f"@{x_rel},{y_rel}")
                selected_data_text.insert(index, drag_data['text'] + "\n")
            except tk.TclError:
                selected_data_text.insert(tk.END, drag_data['text'] + "\n")
        
        drag_data['text'] = None
        
    root.unbind('<ButtonRelease-1>')
    root.unbind('<Motion>')

def on_search_button_click():
    global is_uppercase
    nip_do_szukania = nip_entry.get().strip()
    if not nip_do_szukania:
        messagebox.showwarning("Błąd", "Proszę wprowadzić numer NIP.")
        return

    dane = pobierz_dane_gus_gui(nip_do_szukania)
    if dane:
        
        address_combine_var.set(False)
        zip_city_combine_var.set(False)
        
        entry_frames['Numer Nieruchomości'].grid()
        entry_frames['Miejscowość'].grid()

        for label_text, key in pola_do_wyswietlenia:
            value = str(dane.get(key, "")).strip()
            original_data[label_text] = value
            entry = entry_widgets[label_text]
            entry.config(state=tk.NORMAL)
            entry.delete(0, tk.END)
            entry.insert(0, value)
            entry.config(state='readonly')
        
        nazwa_firmy = dane.get('Nazwa', 'Brak nazwy')
        historia_wpis = f"{nip_do_szukania} | {nazwa_firmy}"
        if historia_wpis not in search_history:
            search_history.append(historia_wpis)
            if len(search_history) > 20: 
                search_history.pop(0)
            update_history_display()
            save_history()
        
        is_uppercase = False
        uppercase_button.config(text="A/a")
        
    else:
        for label_text, key in pola_do_wyswietlenia:
            entry = entry_widgets[label_text]
            entry.config(state=tk.NORMAL)
            entry.delete(0, tk.END)
            entry.config(state='readonly')
            
        entry_frames['Numer Nieruchomości'].grid()
        entry_frames['Miejscowość'].grid()


def combine_entry_data():
    """Generuje tekst do wydruku PDF z danymi z lewego panelu, w zależności od stanu 'is_uppercase'."""
    combined_text = ""
    for label_text, key in pola_do_wyswietlenia:
        if entry_frames[label_text].winfo_ismapped():
            entry_value = entry_widgets[label_text].get()
            if is_uppercase:
                 combined_text += f"{label_text.upper()}: {entry_value.upper()}\n"
            else:
                 combined_text += f"{label_text}: {entry_value}\n"
    return combined_text

def clear_left_panel():
    global is_uppercase
    for label_text, key in pola_do_wyswietlenia:
        entry = entry_widgets[label_text]
        entry.config(state=tk.NORMAL)
        entry.delete(0, tk.END)
        entry.config(state='readonly')
        entry_labels_widget[label_text].config(text=label_text + ":")
    nip_entry.delete(0, tk.END)
    
    address_combine_var.set(False)
    zip_city_combine_var.set(False)
    entry_frames['Numer Nieruchomości'].grid()
    entry_frames['Miejscowość'].grid()
    
    is_uppercase = False
    uppercase_button.config(text="A/a")

    messagebox.showinfo("Sukces", "Dane w lewym panelu zostały wyczyszczone.")

def clear_right_panel():
    selected_data_text.delete(1.0, tk.END)
    messagebox.showinfo("Sukces", "Prawy panel został wyczyszczony.")

# --- FUNKCJE OBSŁUGUJĄCE LOGIKĘ ŁĄCZENIA/ROZDZIELANIA ---

def combine_address_logic():
    ulica_entry = entry_widgets["Ulica"]
    nr_budynku_entry = entry_widgets["Numer Nieruchomości"]
    ulica_val = ulica_entry.get().strip()
    nr_budynku_val = nr_budynku_entry.get().strip()
    
    combined_text = f"{ulica_val} {nr_budynku_val}".strip()
    
    ulica_entry.config(state=tk.NORMAL)
    nr_budynku_entry.config(state=tk.NORMAL)
    
    ulica_entry.delete(0, tk.END)
    ulica_entry.insert(0, combined_text)
    
    nr_budynku_entry.delete(0, tk.END)
    
    ulica_entry.config(state='readonly')
    nr_budynku_entry.config(state='readonly')
    entry_frames['Numer Nieruchomości'].grid_remove()

def split_address_logic():
    ulica_entry = entry_widgets["Ulica"]
    nr_budynku_entry = entry_widgets["Numer Nieruchomości"]
    ulica_val = ulica_entry.get().strip()
    
    parts = ulica_val.rsplit(' ', 1) # rsplit by splitować od prawej (dla adresów)
    
    ulica_entry.config(state=tk.NORMAL)
    ulica_entry.delete(0, tk.END)
    
    nr_budynku_entry.config(state=tk.NORMAL)
    nr_budynku_entry.delete(0, tk.END)
    
    if len(parts) == 2:
        ulica_entry.insert(0, parts[0])
        nr_budynku_entry.insert(0, parts[1])
    else:
        ulica_entry.insert(0, ulica_val)
    
    ulica_entry.config(state='readonly')
    nr_budynku_entry.config(state='readonly')
    entry_frames['Numer Nieruchomości'].grid()

def combine_zip_city_logic():
    kod_pocztowy_entry = entry_widgets["Kod pocztowy"]
    miejscowosc_entry = entry_widgets["Miejscowość"]
    kod_pocztowy_val = kod_pocztowy_entry.get().strip()
    miejscowosc_val = miejscowosc_entry.get().strip()
    
    combined_text = f"{kod_pocztowy_val} {miejscowosc_val}".strip()
    
    kod_pocztowy_entry.config(state=tk.NORMAL)
    miejscowosc_entry.config(state=tk.NORMAL)
    
    kod_pocztowy_entry.delete(0, tk.END)
    kod_pocztowy_entry.insert(0, combined_text)
    
    miejscowosc_entry.delete(0, tk.END)
    
    kod_pocztowy_entry.config(state='readonly')
    miejscowosc_entry.config(state='readonly')
    entry_frames['Miejscowość'].grid_remove()

def split_zip_city_logic():
    kod_pocztowy_entry = entry_widgets["Kod pocztowy"]
    miejscowosc_entry = entry_widgets["Miejscowość"]
    kod_pocztowy_val = kod_pocztowy_entry.get().strip()
    
    parts = kod_pocztowy_val.split(' ', 1) # split by splitować od lewej (dla kodów)
    
    kod_pocztowy_entry.config(state=tk.NORMAL)
    kod_pocztowy_entry.delete(0, tk.END)
    
    miejscowosc_entry.config(state=tk.NORMAL)
    miejscowosc_entry.delete(0, tk.END)
    
    if len(parts) == 2:
        kod_pocztowy_entry.insert(0, parts[0])
        miejscowosc_entry.insert(0, parts[1])
    else:
        kod_pocztowy_entry.insert(0, kod_pocztowy_val)
    
    kod_pocztowy_entry.config(state='readonly')
    miejscowosc_entry.config(state='readonly')
    entry_frames['Miejscowość'].grid()

def handle_address_checkbox():
    if address_combine_var.get():
        combine_address_logic()
    else:
        split_address_logic()

def handle_zip_city_checkbox():
    if zip_city_combine_var.get():
        combine_zip_city_logic()
    else:
        split_zip_city_logic()

# --- Nowa funkcja do ładowania NIP-u z historii ---
def load_nip_from_history(event):
    try:
        index = history_text.index("@%s,%s" % (event.x, event.y))
        line_num = int(index.split('.')[0])
        line_content = history_text.get(f"{line_num}.0", f"{line_num}.end").strip()
        
        if '|' in line_content:
            nip = line_content.split('|')[0].strip()
            
            nip_entry.delete(0, tk.END)
            nip_entry.insert(0, nip)
            on_search_button_click()
            
    except tk.TclError:
        pass
        
def toggle_case():
    """Przełącza między dużymi a domyślnymi literami w polach Entry i etykietach."""
    global is_uppercase
    
    labels_to_change = [
        "Regon", "Typ", "Nazwa", "Województwo", "Powiat", "Gmina",
        "Kod pocztowy", "Miejscowość", "Ulica", "Numer Nieruchomości",
        "Informacja o skreśleniu z REGON"
    ]

    if is_uppercase:
        
        for label_text, entry in entry_widgets.items():
            entry.config(state=tk.NORMAL)
            entry.delete(0, tk.END)
            entry.insert(0, original_data.get(label_text, ""))
            entry.config(state='readonly')
        

        for label_text in labels_to_change:
            entry_labels_widget[label_text].config(text=label_text + ":")

        uppercase_button.config(text="A/a")
        is_uppercase = False
        
    else:
        # Zmiana na duże litery
        for label_text, entry in entry_widgets.items():
            current_text = entry.get()
            uppercase_text = current_text.upper()
            
            entry.config(state=tk.NORMAL)
            entry.delete(0, tk.END)
            entry.insert(0, uppercase_text)
            entry.config(state='readonly')
        
        for label_text in labels_to_change:
            uppercase_label = label_text.upper() + ":"
            entry_labels_widget[label_text].config(text=uppercase_label)

        uppercase_button.config(text="a/A")
        is_uppercase = True

# --- Konfiguracja głównego okna Tkinter ---

root = tk.Tk()
root.title("Baza Internetowa REGON")
root.geometry("1120x720")

main_frame = tk.Frame(root)
main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

# Lewa kolumna (Inputy z danymi)
left_frame = tk.Frame(main_frame)
left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))

input_frame = tk.Frame(left_frame, padx=10, pady=10)
input_frame.pack(padx=5, pady=5, fill=tk.X)

nip_label = tk.Label(input_frame, text="NIP:")
nip_label.pack(side=tk.LEFT, padx=(0, 10))

nip_entry = tk.Entry(input_frame, width=20)
nip_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)
nip_entry.insert(0, "5261040828")

search_button = tk.Button(input_frame, text="Szukaj", command=on_search_button_click)
search_button.pack(side=tk.LEFT, padx=(10, 0))

data_frame = tk.Frame(left_frame, padx=10, pady=10)
data_frame.pack(fill=tk.BOTH, expand=True)
data_frame.columnconfigure(1, weight=1)

pola_do_wyswietlenia = [
    ("Regon", "Regon"), ("Typ", "Typ"), ("Nazwa", "Nazwa"),
    ("Województwo", "Wojewodztwo"), ("Powiat", "Powiat"),
    ("Gmina", "Gmina"), 
    ("Kod pocztowy", "KodPocztowy"),
    ("Miejscowość", "Miejscowosc"),
    ("Ulica", "Ulica"),
    ("Numer Nieruchomości", "Numer Nieruchomości"),
    ("Informacja o skreśleniu z REGON", "Informacja o skreśleniu z REGON")
]
entry_widgets = {}
entry_labels = {}
entry_frames = {}
entry_labels_widget = {}

# Checkbox variables
address_combine_var = tk.BooleanVar()
zip_city_combine_var = tk.BooleanVar()

for i, (label_text, key) in enumerate(pola_do_wyswietlenia):
    row_frame = tk.Frame(data_frame)
    row_frame.grid(row=i, column=0, columnspan=2, sticky='w', pady=2)
    
    lbl = tk.Label(row_frame, text=f"{label_text}:", width=27, anchor="w")
    lbl.pack(side=tk.LEFT)
    
    ent = tk.Entry(row_frame, width=30, readonlybackground="lightgray")
    ent.pack(side=tk.LEFT, fill=tk.X, expand=True)
    ent.config(state='readonly')
    
    ent.bind('<Button-1>', lambda event, entry=ent: on_drag_start(event, entry))
    
    if label_text == "Regon":
        uppercase_button = tk.Button(row_frame, text="A/a", command=toggle_case)
        uppercase_button.pack(side=tk.LEFT, padx=(5, 0))

    if label_text == "Ulica":
        combine_checkbox = tk.Checkbutton(row_frame, variable=address_combine_var, command=handle_address_checkbox)
        combine_checkbox.pack(side=tk.LEFT, padx=(5, 0))
    elif label_text == "Kod pocztowy":
        combine_checkbox = tk.Checkbutton(row_frame, variable=zip_city_combine_var, command=handle_zip_city_checkbox)
        combine_checkbox.pack(side=tk.LEFT, padx=(5, 0))

    entry_widgets[label_text] = ent
    entry_labels[ent] = label_text
    entry_frames[label_text] = row_frame
    entry_labels_widget[label_text] = lbl

pdf_all_button = tk.Button(left_frame, text="Pobierz do PDF", 
                           command=lambda: export_to_pdf_from_widget(combine_entry_data(), f"REGON_Raport_{nip_entry.get().strip()}"))
pdf_all_button.pack(pady=(10, 5))

clear_left_button = tk.Button(left_frame, text="Wyczyść dane", command=clear_left_panel)
clear_left_button.pack(pady=(0, 10))

# Prawa kolumna (nowe okno do kopiowania/edycji)
right_frame = tk.Frame(main_frame)
right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

selected_data_label = tk.Label(right_frame, text="Wybrane dane do wydruku (przeciągnij tutaj):")
selected_data_label.pack(pady=(10, 5))

selected_data_text = scrolledtext.ScrolledText(right_frame, wrap=tk.WORD, width=60, height=15, padx=10, pady=10)
selected_data_text.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)
selected_data_text.config(font=("Courier New", 10))

pdf_selected_button = tk.Button(right_frame, text="Drukuj do PDF wybrane", 
                                command=lambda: export_to_pdf_from_widget(selected_data_text.get(1.0, tk.END), "Wybrany_Raport_REGON"))
pdf_selected_button.pack(pady=(10, 5))

clear_right_button = tk.Button(right_frame, text="Wyczyść wybrane", command=clear_right_panel)
clear_right_button.pack(pady=(0, 10))

# --- SEKCJA HISTORIA ---
history_frame = tk.Frame(root)
history_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)

history_label = tk.Label(history_frame, text="Historia wyszukiwania (NIP | Nazwa firmy):")
history_label.pack()

history_text = scrolledtext.ScrolledText(history_frame, wrap=tk.WORD, width=60, height=8, padx=5, pady=5)
history_text.pack(fill=tk.BOTH, expand=True)
history_text.config(state=tk.DISABLED, font=("Courier New", 10))

history_text.bind("<Double-Button-1>", load_nip_from_history)

load_history()
root.mainloop()
