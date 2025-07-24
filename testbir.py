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
        # service_url = "https://wyszukiwarkaregon.stat.gov.pl/wsBIR/UslugaBIRzewnPubl.svc"
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
    """Zapisuje listę historii do pliku txt."""
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        for entry in search_history:
            f.write(entry + "\n")

def load_history():
    """Wczytuje historię z pliku txt i aktualizuje pole tekstowe."""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                search_history.append(line.strip())
        update_history_display()

def update_history_display():
    """Aktualizuje zawartość pola historii na podstawie listy w pamięci."""
    history_text.config(state=tk.NORMAL)
    history_text.delete(1.0, tk.END)
    for entry in reversed(search_history):
        history_text.insert(tk.END, entry + "\n")
    history_text.config(state=tk.DISABLED)


# --- Funkcje obsługi GUI i zdarzeń ---

drag_data = {'text': None}

def on_drag_start(event, source_entry):
    drag_data['text'] = f"{entry_labels[source_entry]}: {source_entry.get()}"
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
    nip_do_szukania = nip_entry.get().strip()
    if not nip_do_szukania:
        messagebox.showwarning("Błąd", "Proszę wprowadzić numer NIP.")
        return

    dane = pobierz_dane_gus_gui(nip_do_szukania)
    if dane:
        for label_text, key in pola_do_wyswietlenia:
            entry = entry_widgets[label_text]
            entry.config(state=tk.NORMAL)
            entry.delete(0, tk.END)
            value = str(dane.get(key, "")).strip()
            entry.insert(0, value)
            entry.config(state='readonly')
        
        # --- NOWA FUNKCJONALNOŚĆ HISTORII ---
        nazwa_firmy = dane.get('Nazwa', 'Brak nazwy')
        historia_wpis = f"{nip_do_szukania} | {nazwa_firmy}"
        if historia_wpis not in search_history:
            search_history.append(historia_wpis)
            if len(search_history) > 20: # Ograniczanie historii do np. 20 wpisów
                search_history.pop(0)
            update_history_display()
            save_history()
    else:
        for label_text, key in pola_do_wyswietlenia:
            entry = entry_widgets[label_text]
            entry.config(state=tk.NORMAL)
            entry.delete(0, tk.END)
            entry.config(state='readonly')

def combine_entry_data():
    combined_text = ""
    for label_text, key in pola_do_wyswietlenia:
        entry = entry_widgets[label_text]
        combined_text += f"{label_text}: {entry.get()}\n"
    return combined_text

# --- Konfiguracja głównego okna Tkinter ---

root = tk.Tk()
root.title("Baza Internetowa REGON")

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

pola_do_wyswietlenia = [
    ("Regon", "Regon"), ("Typ", "Typ"), ("Nazwa", "Nazwa"),
    ("Województwo", "Wojewodztwo"), ("Powiat", "Powiat"),
    ("Gmina", "Gmina"), ("Kod pocztowy", "KodPocztowy"),
    ("Miejscowość", "Miejscowosc"), ("Ulica", "Ulica"),
    ("Informacja o skreśleniu z REGON", "Informacja o skreśleniu z REGON")
]
entry_widgets = {}
entry_labels = {}

for label_text, key in pola_do_wyswietlenia:
    row_frame = tk.Frame(data_frame)
    row_frame.pack(fill=tk.X, pady=2)
    
    lbl = tk.Label(row_frame, text=f"{label_text}:", width=25, anchor="w")
    lbl.pack(side=tk.LEFT)
    
    ent = tk.Entry(row_frame, width=30, readonlybackground="lightgray")
    ent.pack(side=tk.RIGHT, fill=tk.X, expand=True)
    ent.config(state='readonly')
    
    ent.bind('<Button-1>', lambda event, entry=ent: on_drag_start(event, entry))

    entry_widgets[label_text] = ent
    entry_labels[ent] = label_text

pdf_all_button = tk.Button(left_frame, text="Pobierz do PDF", 
                           command=lambda: export_to_pdf_from_widget(combine_entry_data(), f"REGON_Raport_{nip_entry.get().strip()}"))
pdf_all_button.pack(pady=10)


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
pdf_selected_button.pack(pady=10)


# --- NOWA SEKCJA HISTORIA ---
history_frame = tk.Frame(root)
history_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)

history_label = tk.Label(history_frame, text="Historia wyszukiwania (NIP | Nazwa firmy):")
history_label.pack()

history_text = scrolledtext.ScrolledText(history_frame, wrap=tk.WORD, width=60, height=5, padx=5, pady=5)
history_text.pack(fill=tk.BOTH, expand=True)
history_text.config(state=tk.DISABLED, font=("Courier New", 10))


# Wczytaj historię po starcie aplikacji
load_history()

# Uruchomienie pętli głównej Tkinter
root.mainloop()