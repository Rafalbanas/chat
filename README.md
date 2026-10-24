# Banas Chat — prywatny czat z Ollamą

> Repozytorium zawiera własną warstwę integracji i konfigurację gotowego Open WebUI.
> Interfejs, logowanie, MFA i historia pochodzą z Open WebUI Inc. i jego współtwórców.
> [Pochodzenie komponentów i warunki użycia](THIRD_PARTY_NOTICES.md) · [MIT dla własnego kodu](LICENSE).

Projekt przygotowany dla Rafała Banasia przy wsparciu OpenAI Codex.
To konfiguracja konkretnego wdrożenia, nie uniwersalny instalator: przed użyciem
na swoim serwerze dostosuj domenę, konta, porty, katalogi, certyfikaty i źródło
metadanych CV Tailora. Skrypty akceptacyjne w `ops/` powstały podczas bootstrapu
przed obowiązkowym MFA; nie omijają MFA i nie są poleceniami do cyklicznego
uruchamiania na cudzej produkcji.

Personalizacja brandingu została przygotowana dla jednoosobowego wdrożenia.
Przy większym wdrożeniu sprawdź warunki Open WebUI opisane w notices.

Aplikacja: **https://chat.banas.dev**. Open WebUI **0.12.3 slim**, SQLite,
Docker Compose, istniejący Nginx i istniejący tunel SSH. Jedna implementacja
interfejsu, własna nazwa, ikona i delikatne dostosowanie stylu. Żadne modele,
konfiguracje Ollamy ani konfiguracja CV Tailora nie są zmieniane.

## Architektura i katalogi

```text
Przeglądarka → Cloudflare HTTPS → IPv6 VPS → Nginx
  → 127.0.0.1:18084 Open WebUI
  → 127.0.0.1:18085 bramka polityki
  → 127.0.0.1:11434 istniejący reverse SSH
  → Ollama 0.40.1 na stacjonarce → RTX 3060
```

DNS: rekord AAAA `chat` wskazuje publiczny IPv6 VPS; proxy Cloudflare włączone.
Dokładny adres origin pozostaje w lokalnej dokumentacji administratora.
Certyfikat origin: istniejący Cloudflare Origin CA, obejmujący `*.banas.dev`,
ważny do 2041-01-05. Publiczny certyfikat przeglądarki zapewnia Cloudflare.
HTTPS origin sprawdzono również osobno z oficjalnym CA, bez wyłączania weryfikacji.
Nie ma nowego tunelu Cloudflared ani nowego konta root dla tunelu.

| Element | Lokalizacja |
| --- | --- |
| Źródła w rozmowie | `/root/chat/private-chat` |
| Instalacja i Compose | `/opt/private-chat` |
| SQLite, rozmowy, ustawienia i modele UI | `/var/lib/private-chat/data` |
| Sekrety uruchomieniowe, tryb 0600 | `/etc/private-chat/app.env` |
| Pierwsze dane logowania, tryb 0600 | `/etc/private-chat/initial-login.txt` |
| Klucz szyfrowania backupów, tryb 0600 | `/etc/private-chat/backup.key` |
| Backupy na osobnym wolumenie | `/storage/private-chat-backups` |
| Host Nginx | `/etc/nginx/sites-available/chat.banas.dev.conf` |
| Ustawienia proxy i zaufane sieci Cloudflare | `/etc/nginx/snippets/private-chat-*.conf` |
| Jednostki | `private-chat.service`, `private-chat-gpu-status.service`, `private-chat-backup.timer` |

Oba kontenery działają jako osobny użytkownik systemowy `privatechat`, bez
powłoki i bez capabilities. Open WebUI ma limit RAM 1100 MiB i 1 CPU, bramka
128 MiB i 0,3 CPU. Porty obu usług nasłuchują tylko na loopback. Nie są używane
root VPS ani publiczne klucze administratora jako tożsamość aplikacji.

Obraz przypięto do digestu dla amd64:
`ghcr.io/open-webui/open-webui@sha256:912c133d2dcecb8d74662f9be64b1f00f303a0d8c0836cbb30fd156f65652f5f`.

## Dostęp i bezpieczeństwo

Jedno konto: `admin@banas.dev`. Hasło startowe odczytaj lokalnie na VPS:

```sh
sudo cat /etc/private-chat/initial-login.txt
```

Nie wysyłaj tego pliku do repozytorium ani do rozmów. Po pierwszym wejściu
zmień hasło i usuń plik startowy. Hasło bootstrap usunięto z pliku środowiska
po utworzeniu konta. Aplikacja przechowuje hash hasła; hasło nie trafia do historii.

Obowiązkowe 2FA jest włączone i przetestowane po odtworzeniu aplikacji; wyniki
opisuje `docs/DEPLOYMENT.md`. Pierwsze
logowanie wymaga przypisania własnej aplikacji TOTP i zapisania kodów odzyskiwania.
Samo poprawne hasło nie daje dostępu do czatu. Nie konfigurujemy za właściciela
sekretu jego aplikacji TOTP.

Zegar VPS jest synchronizowany przez hosta LXC: `NTPSynchronized=yes`.
Sprawdzono orientacyjnie zgodność z zewnętrznym czasem HTTPS. Kody TOTP działają
w 30-sekundowych przedziałach, z tolerancją poprzedniego i następnego przedziału;
strefa wyświetlania godzin nie wpływa na kody. Na telefonie włącz automatyczną datę.

Rejestracja jest wyłączona w aplikacji i blokowana w Nginx. Anonimowe żądania
historii, listy modeli i generowania są odrzucane. Cookies mają Secure, HttpOnly
oraz SameSite=Strict. Niebezpieczne metody HTTP wymagają zgodnego Origin.
CORS dopuszcza wyłącznie domenę czatu. CSP ogranicza źródła skryptów i blokuje
zewnętrzny beacon analityczny Cloudflare. Nie włączamy zdalnego wykonywania kodu,
kluczy API ani bezpośrednich połączeń z dostawcą z przeglądarki.

Logowanie jest ograniczane w Nginx i w Open WebUI. Bramka dopuszcza maksymalnie
12 generowań na minutę i jedną aktywną generację. Nginx ogranicza mutacje API,
a nie pobieranie historii i zasobów interfejsu. IP klienta jest pobierane z
nagłówka Cloudflare wyłącznie dla oficjalnych, zaufanych sieci tej usługi.

Wylogowanie wszystkich urządzeń: panel administratora → Użytkownicy → edycja
konta → wyloguj wszystkie urządzenia. Zmiana hasła również unieważnia sesje.
Dodawanie użytkowników jest dostępne wyłącznie administratorowi; publiczna
rejestracja pozostaje wyłączona. Zachowaj konfigurację prywatnego konta.

## Modele, myślenie i historia

Bramka odkrywa dwa faktycznie zainstalowane modele przez `/api/tags`:

- `qwen3.5:9b` — domyślny, codzienny.
- `qwen3.8-27b-iq2s:latest` — większy; alias bez `:latest` jest normalizowany.

Pozostałych istniejących modeli nie usuwa ani nie modyfikuje. Nazwy, opis i
limity w panelu Open WebUI są presetami aplikacji, nie zmianą modeli Ollamy.
Bramka nie dopuszcza pull/delete/create modeli ani generowania przez alternatywne
endpointy. Oba modele mają twardy limit kontekstu 8192 i odpowiedzi 1536 tokenów.
Parametry klienta nie mogą podnieść tych limitów ani wymusić preloadu.

Historia jest trwała w SQLite, przypisana do konta. Limit wysyłanej historii
jest konserwatywny: budżet 5632 bajtów UTF-8 z rezerwą szablonu i odpowiedzi.
Dłuższe wiadomości otrzymują czytelny błąd HTTP 413; zapisana historia nie jest
po cichu obcinana. To może odrzucać rozmowy wcześniej niż dokładny tokenizer.

Tryb myślenia: Sterowanie → Zaawansowane parametry → `think (Ollama)`.
Domyślnie jest wyłączony. Pola `message.thinking` i `message.content` pozostają
oddzielne w strumieniu; UI pokazuje rozumowanie oddzielnie. Limit wyjścia obejmuje
również myślenie: gdy model zużyje go bez odpowiedzi, pojawi się wskazówka
wyłączenia thinking i ponowienia. Eksport Markdown
lub JSON jest dostępny z menu rozmowy; zbiorczy eksport jest w ustawieniach danych.

## Współdzielenie GPU z CV Tailorem

Istniejące tunele i CV Tailor pozostały niezmienione. Mały, odizolowany proces
systemowy odczytuje wyłącznie stan plików zadań CV Tailora i publikuje do
`/run/private-chat/gpu.json` tylko czas oraz flagę zajętości. Nie udostępnia
czatowi treści CV. Do odczytu chronionych metadanych potrzebuje roota; nie jest
backendem aplikacyjnym, nie ma sieci, a system plików jest dla niego tylko do odczytu
z wyjątkiem własnego katalogu runtime.

Gdy CV Tailor ma zadanie queued/running, bramka odrzuca nowe generowanie.
Gdy zadanie pojawi się w trakcie rozmowy, przerywa własny stream. Stan jest
odświeżany co 0,5 s; brak lub stary stan powoduje odmowę generowania. Nie zmieniamy
globalnych ustawień Ollamy ani semaforów CV Tailora.

To ochrona z priorytetem i odpytywaniem, nie wspólny atomowy mutex obu aplikacji.
Możliwa jest krótka równoczesność do wykrycia nowego zadania, opóźniona dodatkowo
przez planowanie procesów. Pełna atomowa koordynacja wymagałaby zmian również
po stronie CV Tailora, których użytkownik zabronił. Jedna generacja i mały kontekst
ograniczają ryzyko; pamięć modelu zwalnia zgodnie z ustawieniami Ollamy i krótkim
`keep_alive=0` czatu: model jest zwalniany po zakończeniu odpowiedzi, bez
agresywnego ładowania obu modeli. Kolejna wiadomość wymaga ponownego załadowania
modelu. CV Tailor zachowuje własne ustawienia podtrzymywania pamięci (15 minut).

## Eksploatacja

```sh
sudo systemctl status private-chat private-chat-gpu-status
sudo docker compose --project-directory /opt/private-chat --env-file /etc/private-chat/app.env ps
sudo journalctl -u private-chat -u private-chat-gpu-status --since today
sudo docker compose --project-directory /opt/private-chat --env-file /etc/private-chat/app.env logs --tail 50
```

Kontenery mają healthcheck i restart po awarii. Jednostki są włączone na start
systemu. Nie testowano restartu całego VPS, zgodnie z zakazem przerywania innych usług.
Logowanie audytowe treści jest wyłączone; logi kontenerów mają rotację 3 × 5 MB.
Nie włączaj DEBUG ani logowania treści żądań. SQLite i dane wymagają ochrony jak
prywatna korespondencja; nie są automatycznie filtrowane wiadomości wpisane przez właściciela.

## Backup

Codziennie o 04:35 Europe/Warsaw z losowym opóźnieniem do 10 minut. Retencja:
14 udanych kopii. Najpierw wykonywany jest spójny SQLite online backup (uwzględnia
WAL), potem kopia pozostałych danych i konfiguracji, szyfrowanie GPG AES-256,
odtworzenie do izolowanego katalogu oraz kontrola hashy i `PRAGMA integrity_check`.

```sh
sudo systemctl start private-chat-backup.service
sudo systemctl list-timers private-chat-backup.timer
sudo cat /etc/private-chat/last-backup.json
```

**Zachowaj `/etc/private-chat/backup.key` poza VPS, w menedżerze haseł.**
Jest celowo wykluczony z archiwum; utrata klucza uniemożliwia odszyfrowanie kopii.
Backupy są na osobnym wolumenie tego VPS. Zewnętrzna kopia poza dostawcą nie została
skonfigurowana, ponieważ nie wskazano docelowego magazynu.

Test konkretnej kopii bez zmiany produkcji:

```sh
sudo python3 /opt/private-chat/ops/backup.py verify /storage/private-chat-backups/daily-RRRRMMDDTHHMMSSZ.tar.gz.gpg
```

## Aktualizacja

1. Przeczytaj informacje o wydaniu i wybierz konkretny digest obrazu dla amd64.
2. Wykonaj i zweryfikuj backup. Zachowaj aktualny digest oraz plik środowiska.
3. Pobierz nowy obraz, zmień tylko `OPEN_WEBUI_IMAGE` w `/etc/private-chat/app.env`.
4. Sprawdź konfigurację, odtwórz wyłącznie własne kontenery i poczekaj na healthcheck:

```sh
sudo docker compose --project-directory /opt/private-chat --env-file /etc/private-chat/app.env config --quiet
sudo docker compose --project-directory /opt/private-chat --env-file /etc/private-chat/app.env up -d --wait --wait-timeout 240
```

5. Migracje Alembic uruchamia Open WebUI. Sprawdź logowanie, MFA, historię, oba modele,
   stream i anulowanie, a następnie stan banas.dev oraz CV Tailora.
6. Nie używaj `latest`, automatycznych aktualizacji bez backupu ani globalnego prune Dockera.

## Awaria i rollback

- Gdy brakuje Ollamy: sprawdź stacjonarkę i istniejący tunel; nie przebudowuj go ani
  nie udostępniaj Ollamy publicznie. Logowanie i historia nie wymagają GPU.
- Gdy aplikacja nie działa: sprawdź healthcheck oraz limity/dysk, zrestartuj wyłącznie
  `private-chat`; nie restartuj całego VPS ani Nginx bez walidacji konfiguracji.
- Po wadliwej migracji potrzeba **starego obrazu i bazy sprzed migracji**. Sam stary
  obraz na nowszej bazie nie jest bezpiecznym rollbackiem.

Przywrócenie danych wykonuje administrator w oknie serwisowym samego czatu:

1. Zweryfikuj archiwum skryptem powyżej i wykonaj kopię obecnego stanu.
2. Odszyfruj archiwum do nowego katalogu z uprawnieniami 0700, używając GPG
   i klucza z `backup.key`; nie rozpakowuj niezaufanego archiwum jako root.
3. Zatrzymaj wyłącznie kontenery projektu `banas-private-chat` poleceniem Compose `stop`.
4. Zachowaj obecny `data/` pod inną nazwą. Odtwórz katalog `data/` z kopii, przypisz
   właściciela `privatechat:privatechat`. Nie przenoś aktywnych plików WAL z innej bazy.
5. Odtwórz pasujący `configuration/app.env` z archiwum (0600) i kod `project/`.
   Zachowaj stabilny `WEBUI_SECRET_KEY`, potrzebny również do odczytu sekretów MFA.
6. Uruchom pasujący stary digest przez Compose `up -d --wait`; sprawdź integralność,
   logowanie, MFA i historię. Nie cofaj konfiguracji innych hostów Nginx.

## Źródła i wyniki

- Szczegółowy raport: `docs/DEPLOYMENT.md`.
- Prywatny audyt infrastruktury i oryginalna dokumentacja operatora pozostają lokalnie
  jako `docs/AUDIT.md` i `docs/OPERATIONS.local.md`; Git je ignoruje.
- Dokumentacja upstream: https://docs.openwebui.com/getting-started/advanced-topics/hardening/
- MFA: https://docs.openwebui.com/features/authentication-access/mfa/
- Wydanie: https://github.com/open-webui/open-webui/releases/tag/v0.12.3
