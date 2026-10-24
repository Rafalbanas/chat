# Pochodzenie komponentów i licencje

Projekt utrzymuje Rafał Banaś. Własny kod integracyjny, konfiguracja wdrożenia,
testy, ikona SVG i style zostały przygotowane dla tego projektu przy wsparciu
OpenAI Codex. Nie przypisujemy sobie autorstwa interfejsu ani backendu Open WebUI.
Nazwa Banas Chat oznacza to konkretne wdrożenie i warstwę integracji.

## Co pochodzi z tego repozytorium

| Pliki | Zakres |
| --- | --- |
| `config/gateway.py` | Własna bramka do Ollamy: limity, priorytet CV Tailora, osobne thinking, wyładowywanie modeli |
| `ops/gpu_status.py` | Własny odczyt metadanych zajętości CV Tailora |
| `ops/backup.py` | Własna orkiestracja kopii SQLite i plików, szyfrowania GPG oraz testowego odtworzenia |
| `ops/install.py`, `ops/configure_*.py`, `ops/enable_*.py` | Własne skrypty instalacji i konfiguracji; korzystają z publicznych API i narzędzi systemowych |
| `compose.yaml`, `config/*.service`, `config/*.timer`, `config/*.conf` | Konfiguracja integrująca istniejące usługi i obraz upstream |
| `assets/icon.svg`, `assets/brand.css` | Własna ikona i uzupełniające style; nie zawierają logo OpenAI ani skopiowanych assetów Open WebUI |
| `tests/`, skrypty akceptacyjne w `ops/` | Własne testy bramki i wdrożenia |

Oryginalne materiały tego repozytorium udostępniamy na [licencji MIT](LICENSE).
MIT nie zastępuje licencji poniższych projektów, modeli, obrazów kontenerów
ani tekstów licencji w katalogu `licenses/`.

## Projekty zewnętrzne

| Komponent | Wykorzystanie i pochodzenie | Warunki |
| --- | --- | --- |
| Open WebUI 0.12.3 slim | Gotowy interfejs i backend: konta, MFA, historia, modele, Markdown, CodeMirror i eksport. Oficjalny obraz `ghcr.io/open-webui/open-webui`, przypięty digestem w konfiguracji. Autorzy: Open WebUI Inc., projekt utworzony przez Timothy Jaeryang Baek i rozwijany przez współtwórców. | [Open WebUI License dla v0.12.3](https://github.com/open-webui/open-webui/blob/v0.12.3/LICENSE); [lokalna, niezmieniona kopia](licenses/Open-WebUI-v0.12.3.txt) |
| Ollama | Istniejący silnik inferencji na osobnej stacji GPU, wywoływany przez API. Binaria nie są dołączone do repo. | [MIT, copyright Ollama](https://github.com/ollama/ollama/blob/main/LICENSE) |
| aiohttp | Biblioteka HTTP bramki; wykorzystujemy wersję dostarczoną z przypiętym obrazem Open WebUI, bez kopiowania jej źródeł. | [Apache-2.0, aio-libs contributors](https://github.com/aio-libs/aiohttp/blob/master/LICENSE.txt) |
| Docker Compose | Zewnętrzne narzędzie uruchamiające usługi z naszego pliku Compose. | [Apache-2.0](https://github.com/docker/compose/blob/main/LICENSE) |
| Nginx | Istniejące reverse proxy; repo zawiera własną konfigurację, bez kodu i binariów Nginx. | [Licencja BSD-style, Igor Sysoev i Nginx, Inc.](https://nginx.org/LICENSE) |
| SQLite | Baza Open WebUI oraz mechanizm online backup używany przez skrypt Pythona. | [Public domain według autorów SQLite](https://sqlite.org/copyright.html) |
| GnuPG | Osobny program `gpg` wywoływany przez skrypt backupu; nie jest dystrybuowany w repo. | [GPL-3.0-or-later, źródłowy plik COPYING projektu GnuPG](https://github.com/gpg/gnupg/blob/master/COPYING) |
| Playwright | Zewnętrzne narzędzie testów przeglądarkowych; przeglądarka ani biblioteka nie są dołączone do repo. | [Apache-2.0, Microsoft i współtwórcy](https://github.com/microsoft/playwright/blob/main/LICENSE) |
| Cloudflare | Używane DNS, proxy i TLS; lista zaufanych sieci w konfiguracji pochodzi z [publicznego API Cloudflare](https://api.cloudflare.com/client/v4/ips), pobrana 24.10.2026. Kod i infrastruktura Cloudflare nie są częścią repo. | Usługa zewnętrzna na warunkach jej dostawcy |

Repozytorium nie zawiera kopii źródeł Open WebUI, gotowego obrazu kontenera,
wag modeli ani binariów wymienionych narzędzi. Biblioteki dołączone do obrazu
upstream zachowują własne licencje i informacje autorów. Jeżeli budujesz lub
redystrybuujesz własny obraz, zachowaj również zawarte w nim licencje i notices.

## Branding Open WebUI

Licencja v0.12.3 zawiera ograniczenie zmian brandingu. Jednym z wyjątków jest
wdrożenie lub dystrybucja, w których liczba użytkowników z bezpośrednim dostępem
nie przekracza 50 w dowolnym ruchomym okresie 30 dni. Obecne wdrożenie ma jedno
konto, a personalizacja nazwy i ikony korzysta z tego wyjątku.

Publiczny dostęp do tego repozytorium nie otwiera rejestracji w aplikacji.
Jeśli użyjesz konfiguracji dla większej liczby osób, zachowaj oryginalny branding
Open WebUI albo uzyskaj zgodę lub licencję wskazaną w pełnym tekście upstream.
Przed takim wdrożeniem trzeba przejrzeć `WEBUI_NAME`, reguły ikony i `sub_filter`
w Nginx oraz nasze style. Sama wzmianka „powered by” nie zastępuje warunków licencji.

## Modele i ich pochodzenie

Identyfikatory w konfiguracji odnoszą się do modeli wcześniej zainstalowanych
przez właściciela infrastruktury. `qwen3.5:9b` i `qwen3.8-27b-iq2s:latest`
nie są modelami opracowanymi w tym repozytorium. Druga nazwa jest lokalnym aliasem
Ollamy; sama nazwa nie dowodzi dokładnej kwantyzacji ani licencji wag.

Licencję konkretnego modelu należy sprawdzić w jego model card i materiałach
oryginalnego wydawcy oraz autora konwersji. Licencja MIT Ollamy i MIT tego repo
nie udzielają automatycznie praw do dowolnych wag modeli. Nie dołączamy wag ani
nie deklarujemy ich ponownego licencjonowania.

## Znaki i powiązania

Nazwy Open WebUI, Ollama, OpenAI, Docker, Cloudflare i pozostałych projektów
służą identyfikacji użytych narzędzi. Repozytorium nie jest oficjalnym produktem
tych dostawców i nie sugeruje ich patronatu. Nie używa logo ani znaków OpenAI
jako własnej identyfikacji wizualnej.
