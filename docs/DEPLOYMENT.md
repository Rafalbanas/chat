# Raport wdrożenia — 24 października 2026

**Aplikacja działa pod https://chat.banas.dev. Wymagane są hasło i drugi składnik.**
Pierwsze logowanie administratora prowadzi do przypisania własnej aplikacji TOTP;
ukończenie tego kroku oraz zachowanie kodów odzyskiwania należy do właściciela.
Nie przypisano za właściciela żadnego autentykatora.

## Logowanie

Login: `admin@banas.dev`. Dane startowe: `/etc/private-chat/initial-login.txt`,
uprawnienia 0600, właściciel root. Nie ma otwartej rejestracji. Hasło bootstrap
usunięto z pliku środowiska i odtworzono kontener bez niego. Sesje testowe zostały
unieważnione. Żadne hasła ani tokeny sesji nie zostały zapisane w kodzie lub raporcie.

Pierwsze wejście:

1. Odczytaj plik startowy na Mikrusie i otwórz https://chat.banas.dev.
2. Podaj login oraz hasło, przypisz własny autentykator i zatwierdź kod.
3. Zachowaj kody odzyskiwania poza telefonem, zmień hasło i usuń plik startowy.
4. Zachowaj klucz `/etc/private-chat/backup.key` poza VPS.

Zegar: `NTPSynchronized=yes`; kontener LXC korzysta z zegara hosta. Lokalne NTP
jest nieaktywne, co nie oznacza braku synchronizacji zegara hosta. Orientacyjne
porównanie z nagłówkiem Date odpowiedzi HTTPS Google wykazało różnicę około
0,05 s; nie jest to pomiar precyzji NTP. Implementacja TOTP sprawdza bieżący,
poprzedni i następny 30-sekundowy przedział i blokuje ponowne użycie kodu.
Nie zmieniano czasu systemowego ani usług NTP. Strefa konta: Europe/Warsaw.

## Architektura i wybór

Open WebUI 0.12.3 slim zapewnia utrzymywalny interfejs zamiast drugiej własnej
implementacji frontendu. Dodano nazwę Banas Chat, ikonę, style dostępności i mobilne,
polskie opisy modeli i podpowiedzi. Frontend i backend upstream, SQLite, Docker
Compose, istniejący Nginx oraz mała bramka aiohttp egzekwująca limity zasobów.

Kod: `/root/chat/private-chat`; instalacja: `/opt/private-chat`.
Dane: `/var/lib/private-chat/data`. Konfiguracja: `/etc/private-chat/app.env`.

Przeglądarka → Cloudflare HTTPS → publiczny IPv6 Mikrusa → Nginx → Open WebUI
`127.0.0.1:18084` → bramka `127.0.0.1:18085` → istniejący tunel
`127.0.0.1:11434` → lokalna Ollama na stacjonarce. Porty backendów nie nasłuchują
publicznie. Nie instalowano Cloudflared i nie zmieniano konfiguracji tuneli.

Domyślny model: `qwen3.5:9b`. Drugi: `qwen3.8-27b-iq2s:latest`, odkryty pod
rzeczywistą nazwą API. Żaden model ani Modelfile nie został zmieniony.
Obraz przypięto do digestu, kontenery pracują jako `privatechat`, bez capabilities.
Maksymalnie jedna generacja, 8192 kontekstu i 1536 tokenów wyjścia; konserwatywna
kontrola tekstu przed wywołaniem GPU. Bramka odmawia generowania, gdy metadane
zadań CV Tailora wskazują aktywność. Ograniczenia tej ochrony opisano w README.

## Rzeczywiste wyniki testów

| Test | Wynik |
| --- | --- |
| Publiczny HTTPS | HTTP 200, walidacja publicznego TLS poprawna (`TLS=0`) |
| HTTPS origin | Poprawna walidacja certyfikatu z oficjalnym Cloudflare Origin CA |
| Anonimowa historia/lista modeli/generowanie | HTTP 401 |
| Publiczna rejestracja | HTTP 403 |
| Mutacja z obcego Origin | HTTP 403 |
| Konto administratora | Logowanie przetestowane przed włączeniem obowiązkowego MFA |
| Cookies sesji | Secure, HttpOnly, SameSite=Strict potwierdzone w odpowiedzi logowania |
| Zmiana MFA i sesje | Włączenie MFA unieważniło dotychczasowy token; odczyt historii HTTP 401 |
| Poprawne hasło po włączeniu MFA | Wyłącznie `next_step=enroll`, bez sesyjnego tokenu i cookie |
| Token wyzwania MFA | Historia i generowanie nadal HTTP 401 |
| MFA po odtworzeniu kontenera | Nadal wymagane; pełna sesja nie jest wydawana po samym haśle |
| Rate limiting logowania | Cztery błędne próby HTTP 400, kolejna HTTP 429 w kontrolowanym teście lokalnym |
| Linki publicznego udostępniania rozmów | HTTP 403, również `/s/` |
| Wykrywanie modeli | API zwróciło oba wymagane identyfikatory |
| Nowa rozmowa, nazwa, wyszukiwanie | Zapis, zmiana nazwy i znalezienie rozmowy potwierdzone |
| Qwen 3.5 9B po polsku, natywny streaming | 59 fragmentów, pierwszy po 4,50 s, całość 5,59 s |
| Qwen 3.8 27B po polsku, natywny streaming | 69 fragmentów, pierwszy po 5,33 s, całość 8,61 s |
| 9B w przeglądarce | Rzeczywiste generowanie kodu Python, zapis i otwarcie rozmowy |
| 27B w przeglądarce | Wybór z przełącznika, wygenerowana odpowiedź i zachowanie po odświeżeniu |
| Thinking | Osobne pole `message.thinking`; ustawienie `think (Ollama)` widoczne w Sterowaniu |
| Zbyt długi kontekst | HTTP 413 przed rozpoczęciem generowania |
| Anulowanie w UI | Przycisk „Przerwij” wywołał zatrzymanie zadania, HTTP 200 |
| Ponowienie w UI | „Wygeneruj ponownie” → „Spróbuj ponownie”, nowe żądanie HTTP 200; ponowione zadanie również zatrzymano |
| Markdown, listy, tabele i kod | Przetestowane w Chromium; kod renderowany przez CodeMirror z podświetleniem |
| Kopiowanie kodu | Schowek zawierał dokładnie `print(2 + 2)` |
| XSS w Markdown | Wstrzyknięty script i onerror nie wykonały się; zawartość pokazano jako tekst |
| Historia po odtworzeniu aplikacji | Historia z rzeczywistą odpowiedzią była identyczna przed i po odtworzeniu kontenera |
| Unieważnienie wszystkich sesji | Stary bearer otrzymał 401; nowe logowanie działało przed włączeniem MFA |
| Usunięcie rozmowy | HTTP 200; późniejszy dostęp do tej rozmowy HTTP 401 |
| Eksport historii | Zweryfikowany NDJSON/JSON z identyfikatorem zapisanej rozmowy |
| Telefon | Widok 390 × 844 bez poziomego przewijania; obecny kompozytor i rozmowa |
| Bramka | 8/8 testów jednostkowych/integracyjnych: kontekst, modele, pojedyncza generacja, priorytet CV, stare metadane, thinking i zakaz mutacji modeli |
| Backup | Szyfrowanie GPG AES-256, kontrola hashy i odtworzenie SQLite z `integrity_check=ok` |
| Autostart | Wszystkie trzy jednostki aplikacji/monitora/backupów mają stan enabled |

Czasy modeli są jednorazowymi pomiarami krótkich odpowiedzi, nie gwarancją
wydajności dłuższych rozmów. Przeglądarka przechodziła przez rzeczywistą domenę
publiczną, bez wyłączania kontroli TLS. Zablokowany beacon analityczny Cloudflare
jest oczekiwanym skutkiem polityki prywatności CSP.

Tryb thinking może wykorzystać limit wyjścia przed napisaniem odpowiedzi.
Zaobserwowano to przy limitach testowych 256 i 1024 tokenów. Bramka zachowuje
thinking oddzielnie, a wyczerpanie budżetu bez odpowiedzi daje teraz czytelny
komunikat błędu i wskazówkę wyłączenia thinking. Nie zwiększono niekontrolowanie
kontekstu ani obciążenia GPU; domyślny tryb bez thinking działa poprawnie.

## Stan dotychczasowych usług

Porównano 21 istniejących plików konfiguracji Nginx i Caddy z kopią sprzed
instalacji: **żaden nie został zmieniony**. Dodano wyłącznie pliki hosta czatu.
Nginx przeładowywano łagodnie po udanej walidacji `nginx -t`.

- `banas.dev`: HTTP 200, publiczny TLS poprawny.
- `cv.banas.dev`: HTTP 303 do logowania, tak samo jak przed zmianami.
- Healthcheck CV Tailora: `{"status":"ok"}`.
- Nginx, Caddy i SSH: active.
- SSH: porty 22/1022 nadal nasłuchują.
- Reverse SSH: loopback 22022 i 11434, te same procesy sshd co na początku audytu.
- Tunel do Ollamy sprawdzono rzeczywistymi generowaniami obu modeli.

Nie uruchamiano pełnej operacji tworzenia CV ani nie zmieniano danych lub
konfiguracji CV Tailora. Nie wykonano restartu VPS ani stacjonarki. Osobnego
logowania SSH na stacjonarkę nie zakończono, bo brakowało wcześniej zaufanego
klucza hosta dla portu 22022; nie wyłączano weryfikacji tego klucza.

## Utrzymanie i ograniczenia

Dokładne polecenia aktualizacji, backupu i rollbacku: `README.md`.
Backup codziennie o 04:35 Europe/Warsaw + do 10 min opóźnienia; 14 kopii,
osobny wolumen `/storage`, każda kopia szyfrowana i testowo odtwarzana.
Zachowaj klucz backupów poza serwerem; zewnętrznego magazynu nie wskazano.

Pełnego logowania TOTP i użycia kodu odzyskiwania nie wykonano za właściciela.
Te czynności wymagają jego autentykatora. Po stronie serwera sprawdzono obowiązek
MFA, brak sesji po samym haśle i brak dostępu przy użyciu tokenu wyzwania.
Nie testowano osobno eksportu Markdown i ręcznego przełączania motywu; funkcje
są dostępne w standardowym interfejsie Open WebUI. Nie deklarujemy tych czynności
jako wykonanych testów.

Ochrona CV Tailora jest reaktywna, z odpytywaniem metadanych; nie jest atomowym
wspólnym planistą GPU. Nie zmieniano CV Tailora, aby taki planista powstał.
Usunięto wyłącznie rozmowy o zarejestrowanych identyfikatorach testowych;
nie wykonywano masowego usuwania po tytułach.

## Końcowy pomiar zasobów

Open WebUI: 315,9 MiB RAM, około 0,20% CPU w momencie pomiaru.
Bramka: 32,38 MiB RAM, 0% CPU. VPS: około 2150 MiB pamięci dostępnej,
7,1 GiB wolnego na root i 46 GiB wolnego na osobnym /storage.
Oba kontenery: healthy. Backend i bramka nasłuchują tylko na 127.0.0.1.
Pomiar jest chwilowy, nie stanowi testu wielodniowego.

## Zmiana zwalniania modeli — 24.10.2026, 07:02 Europe/Warsaw

Na prośbę właściciela czat wymusza teraz `keep_alive=0` zamiast 60 sekund.
Dotyczy obu dopuszczonych modeli, bez możliwości nadpisania z przeglądarki.
Nie zmieniono ustawień CV Tailora (jego keep_alive wynosi 15 minut), modeli,
serwisu Ollamy ani tuneli. Zrestartowano tylko bramkę, przy pustej liście modeli.

Test rzeczywisty: odpowiedź qwen3.5:9b zakończona po 3,35 s, dwa fragmenty
strumienia; po 0,18 s od zakończenia `/api/ps` zwróciło `{"models":[]}`.
Istniejący komplet 8 testów bramki przeszedł. Publiczny czat HTTP 200/TLS poprawny,
healthcheck CV Tailora `ok`. Model 27B nie był ponownie ładowany w tym teście;
wykorzystuje tę samą, bezwarunkową politykę wyładowania. Kolejna wiadomość
wymaga ponownego ładowania modelu.

Poprzednia konfiguracja: `/storage/private-chat-backups/before-keepalive-20261024T050233Z`.
