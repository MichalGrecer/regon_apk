import litex.regon as regon
import lxml.etree
import tkinter as tk
from tkinter import messagebox, scrolledtext
from datetime import date

def pobierz_dane_gus_gui(nip, output_text_widget):
    
    
    klucz_uzytkownika = "abcde12345abcde12345"
    klient = None
    wyniki_do_wyswietlenia = []

    try:
       
        #service_url = "https://wyszukiwarkaregontest.stat.gov.pl/wsBIR/UslugaBIRzewnPubl.svc" # Adres testowy
        service_url = "https://wyszukiwarkaregon.stat.gov.pl/wsBIR/UslugaBIRzewnPubl.svc" # Adres produkcyjny
        klient = regon.REGONAPI(service_url)

        
        klient.login(klucz_uzytkownika)

        
        wynik_wyszukiwania = klient.search(nip=nip, detailed=True)
        if not wynik_wyszukiwania:
            wyniki_do_wyswietlenia.append(f"Nie znaleziono podmiotu dla NIPu: {nip}")
            return "\n".join(wyniki_do_wyswietlenia)

        glowny_element_odpowiedzi = wynik_wyszukiwania[0]

        
        dane_do_raportu = {}
        
        #Podstawowe pola bezpośrednio z głównego elementu <dane>
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
            # Pobierz element praw_dataZakonczeniaDzialalnosci
            raw_data_zakonczenia_element = getattr(detailed_element, 'praw_dataZakonczeniaDzialalnosci', None)
            data_zakonczenia_text = raw_data_zakonczenia_element.text if raw_data_zakonczenia_element is not None else None

            if data_zakonczenia_text and data_zakonczenia_text.strip():
                dane_do_raportu['Informacja o skreśleniu z REGON'] = f"Działalność zakończona: {data_zakonczenia_text.strip()}"
            else:
                dane_do_raportu['Informacja o skreśleniu z REGON'] = "----------"
        else:
            dane_do_raportu['Informacja o skreśleniu z REGON'] = "----------" # Jeśli brak sekcji detailed

        # Formatowanie wyjścia
        pola_do_wyswietlenia = [
            ("Regon", "Regon"),
            ("Typ", "Typ"),
            ("Nazwa", "Nazwa"),
            ("Województwo", "Wojewodztwo"),
            ("Powiat", "Powiat"),
            ("Gmina", "Gmina"),
            ("Kod pocztowy", "KodPocztowy"),
            ("Miejscowość", "Miejscowosc"),
            ("Ulica", "Ulica"),
            ("Informacja o skreśleniu z REGON", "Informacja o skreśleniu z REGON")
        ]

        # Wyrównanie kolumn
        max_label_len = max(len(label) for label, _ in pola_do_wyswietlenia)
        
        for label, key in pola_do_wyswietlenia:
            value = str(dane_do_raportu.get(key, "")).strip()
            wyniki_do_wyswietlenia.append(f"{label.ljust(max_label_len)} {value}")
        
        return "\n".join(wyniki_do_wyswietlenia)

    except Exception as e:
        message = f"Wystąpił błąd: {e}"
        return message

    finally:
        try:
            if klient:
                klient.logout()
        except Exception:
            pass # Ignoruj błędy wylogowania


def on_search_button_click():
    """Funkcja wywoływana po kliknięciu przycisku 'Szukaj'."""
    nip_do_szukania = nip_entry.get().strip()
    if not nip_do_szukania:
        messagebox.showwarning("Błąd", "Proszę wprowadzić numer NIP.")
        return

    output_text.delete(1.0, tk.END) # Wyczyść poprzednie wyniki
   
    output_text.insert(tk.END, f"Stan danych na dzień: {get_current_date()}\n\n") 

    
    wynik_pobierania = pobierz_dane_gus_gui(nip_do_szukania, output_text)
    output_text.insert(tk.END, wynik_pobierania)

def get_current_date():
    """Pobiera aktualną datę w formacie DD-MM-YYYY."""
  
    return date.today().strftime("%d-%m-%Y")

# Konfiguracja głównego okna Tkinter
root = tk.Tk()
root.title("Baza Internetowa REGON")

# Ramka na wprowadzanie NIP-u
input_frame = tk.Frame(root, padx=10, pady=10)
input_frame.pack(padx=5, pady=5, fill=tk.X)

# Etykieta i pole dla NIP
nip_label = tk.Label(input_frame, text="NIP:")
nip_label.pack(side=tk.LEFT, padx=(0, 10))

nip_entry = tk.Entry(input_frame, width=20)
nip_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)
nip_entry.insert(0, "5261040828") # Domyślny NIP do testów

search_button = tk.Button(input_frame, text="Szukaj", command=on_search_button_click)
search_button.pack(side=tk.LEFT, padx=(10, 0)) #  położenie przycisku

# Pole tekstowe do wyświetlania wyników
output_text = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=60, height=15, padx=10, pady=10) # Zmniejszamy rozmiar okna
output_text.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)
output_text.config(font=("Courier New", 10)) # Czcionka o stałej szerokości dla wyrównania

# Uruchomienie pętli głównej Tkinter
root.mainloop()