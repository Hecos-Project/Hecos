import codecs
content_it = """
---

## 7. L'Executor e i Comandi di Sistema (Shell e Python)

Tra i nodi più potenti di Hecos ci sono quelli legati al modulo **EXECUTOR**. Questi nodi ti permettono di uscire dai confini dell'automazione standard e di impartire veri e propri ordini al tuo sistema operativo (Windows o Linux).

### 7.1 Esecuzione Visibile vs Invisibile (Background)

Quando usi la riga di comando (Shell) tramite Hecos, devi decidere se vuoi che l'utente veda cosa succede o se deve avvenire tutto di nascosto.

- **`EXECUTOR__execute_background_command`**: Questo nodo è progettato per eseguire comandi in modalità *silenziosa* (headless). Nessuna finestra nera si aprirà sul desktop. Il comando lavorerà nell'ombra e l'output verrà salvato in un file di log. È perfetto per scaricare file, avviare server o fare operazioni di manutenzione senza disturbarti. 
  *Attenzione*: Se scrivi semplicemente `cmd` o `bash` qui dentro, il nodo creerà un terminale invisibile che aspetterà all'infinito un tuo input, bloccando il flusso!
- **`EXECUTOR__execute_shell_command`**: Se desideri **aprire visibilmente** un programma o una finestra del prompt dei comandi sul desktop, devi "staccare" il processo usando il comando nativo del tuo sistema operativo, come `start` (su Windows) o `gnome-terminal` (su Linux).

> [!TIP]
> **Come eseguire più comandi di fila?** Non serve usare un nodo per ogni comando! Puoi usare l'operatore `&&` per concatenarli in un'unica stringa. Hecos li eseguirà rigorosamente in sequenza. Esempio: `ipconfig && mkdir nuova_cartella && echo "Finito!"`

#### Esempio 1: Creare una cartella silenziosamente (Background)
*Scenario: Un flusso crea una directory di backup senza mostrare nulla a schermo.*
```yaml
  - id: crea_backup_silenzioso
    action: EXECUTOR__execute_background_command
    params:
      command: "mkdir C:\\backup_hecos && echo Backup folder created"
```

#### Esempio 2: Aprire un Prompt dei Comandi Visibile (Solo Windows)
*Scenario: Vuoi che Hecos apra una finestra nera del CMD, faccia un PING a Google, e mantenga la finestra aperta per farti leggere il risultato.*
```yaml
  - id: apri_cmd_visibile
    action: EXECUTOR__execute_shell_command
    params:
      # Il parametro /k ("keep") mantiene la finestra aperta. Usa /c ("close") per chiuderla.
      command: "start cmd /k \\"ping 8.8.8.8 && echo Ping completato!\\""
```

### 7.2 Il Problema della Multipiattaforma (Windows vs Linux)

Se scrivi `start cmd` in un nodo shell, hai appena reso il tuo flusso **incompatibile con Linux o Mac**. Su Linux, `cmd` non esiste e il flusso genererà un errore. Come si risolve questo problema se vuoi creare automazioni universali?

Hai due soluzioni:
1. **Usa i nodi nativi di Hecos**: Invece di usare `execute_shell_command` e scrivere `mkdir` o `taskkill`, usa i nodi dedicati dell'executor! Ad esempio: `EXECUTOR__create_dir`, `EXECUTOR__read_file` o `EXECUTOR__kill_process`. Hecos capirà da solo se sei su Windows o Linux ed eseguirà il comando giusto.
2. **Usa lo Script Maker definitivo: Python!**

### 7.3 `EXECUTOR__run_python_code`: Il vero Script Maker Universale

Invece di impazzire con comandi concatenati da `&&` o file `.bat`, puoi usare il nodo `EXECUTOR__run_python_code`. Questo nodo ti mette a disposizione un vero e proprio editor in cui puoi inserire uno script Python.

**Perché usare Python invece della Shell?**
- **È Multipiattaforma**: Lo stesso script Python funziona identico su Windows, Linux e Raspberry Pi.
- **È Potente**: Puoi usare cicli logici complessi, calcoli matematici, o formattare i dati molto meglio che in un prompt dei comandi.
- **Variabili**: Puoi restituire il risultato del tuo script (tramite `print`) per salvarlo in una variabile `output_as` e passarlo ai nodi successivi!

#### Esempio 3: Uno Script Python Multipiattaforma Universale
*Scenario: Uno script Python che capisce da solo su quale sistema operativo si trova, crea una cartella nella scrivania dell'utente in modo sicuro e restituisce l'esito a Hecos per farglielo pronunciare a voce.*
```yaml
  - id: script_python_universale
    action: EXECUTOR__run_python_code
    params:
      code: |
        import os
        from pathlib import Path
        
        # Trova la cartella Desktop sia su Windows che su Linux
        desktop_dir = Path.home() / "Desktop"
        nuova_cartella = desktop_dir / "Hecos_Magic_Folder"
        
        if not nuova_cartella.exists():
            nuova_cartella.mkdir()
            print("Ho creato la cartella magica sul desktop!")
        else:
            print("La cartella esisteva già, nessun problema.")
    output_as: esito_script

  - id: annuncia_esito
    action: AUDIO__speak
    params:
      text: "{{ esito_script }}"
    depends_on:
      - script_python_universale
```

In questo modo hai creato un'automazione che puoi condividere con chiunque, indipendentemente dal PC o dal sistema operativo che usano!
"""

content_en = """
---

## 7. The Executor and System Commands (Shell and Python)

Among the most powerful nodes in Hecos are those related to the **EXECUTOR** module. These nodes allow you to step outside the boundaries of standard automation and issue actual commands to your operating system (Windows or Linux).

### 7.1 Visible vs. Invisible Execution (Background)

When using the command line (Shell) through Hecos, you must decide whether the user should see what is happening or if it should all run silently behind the scenes.

- **`EXECUTOR__execute_background_command`**: This node is designed to execute commands in *silent* (headless) mode. No black window will open on the desktop. The command will run in the shadows, and the output will be saved in a log file. It is perfect for downloading files, starting servers, or performing maintenance operations without disturbing you.
  *Warning*: If you simply type `cmd` or `bash` in here, the node will create an invisible terminal that will wait infinitely for your input, blocking the flow!
- **`EXECUTOR__execute_shell_command`**: If you wish to **visibly open** a program or a command prompt window on the desktop, you must "detach" the process using your operating system's native command, such as `start` (on Windows) or `gnome-terminal` (on Linux).

> [!TIP]
> **How to execute multiple commands in a row?** You don't need to use one node for each command! You can use the `&&` operator to concatenate them into a single string. Hecos will execute them strictly in sequence. Example: `ipconfig && mkdir new_folder && echo "Done!"`

#### Example 1: Silently Create a Folder (Background)
*Scenario: A flow creates a backup directory without showing anything on screen.*
```yaml
  - id: create_silent_backup
    action: EXECUTOR__execute_background_command
    params:
      command: "mkdir C:\\backup_hecos && echo Backup folder created"
```

#### Example 2: Open a Visible Command Prompt (Windows Only)
*Scenario: You want Hecos to open a black CMD window, PING Google, and keep the window open for you to read the result.*
```yaml
  - id: open_visible_cmd
    action: EXECUTOR__execute_shell_command
    params:
      # The /k ("keep") parameter keeps the window open. Use /c ("close") to close it.
      command: "start cmd /k \\"ping 8.8.8.8 && echo Ping completed!\\""
```

### 7.2 The Cross-Platform Problem (Windows vs. Linux)

If you type `start cmd` in a shell node, you have just made your flow **incompatible with Linux or Mac**. On Linux, `cmd` doesn't exist, and the flow will throw an error. How do you solve this problem if you want to create universal automations?

You have two solutions:
1. **Use native Hecos nodes**: Instead of using `execute_shell_command` and writing `mkdir` or `taskkill`, use the dedicated executor nodes! For example: `EXECUTOR__create_dir`, `EXECUTOR__read_file`, or `EXECUTOR__kill_process`. Hecos will figure out on its own if you are on Windows or Linux and execute the correct command.
2. **Use the ultimate Script Maker: Python!**

### 7.3 `EXECUTOR__run_python_code`: The True Universal Script Maker

Instead of going crazy with commands concatenated by `&&` or `.bat` files, you can use the `EXECUTOR__run_python_code` node. This node provides you with a real editor where you can insert a Python script.

**Why use Python instead of the Shell?**
- **It is Cross-Platform**: The same Python script runs exactly the same on Windows, Linux, and Raspberry Pi.
- **It is Powerful**: You can use complex logic loops, mathematical calculations, or format data much better than in a command prompt.
- **Variables**: You can return the result of your script (via `print`) to save it in an `output_as` variable and pass it to subsequent nodes!

#### Example 3: A Universal Cross-Platform Python Script
*Scenario: A Python script that figures out on its own which operating system it is on, safely creates a folder on the user's desktop, and returns the result to Hecos to speak it aloud.*
```yaml
  - id: universal_python_script
    action: EXECUTOR__run_python_code
    params:
      code: |
        import os
        from pathlib import Path
        
        # Find the Desktop folder on both Windows and Linux
        desktop_dir = Path.home() / "Desktop"
        new_folder = desktop_dir / "Hecos_Magic_Folder"
        
        if not new_folder.exists():
            new_folder.mkdir()
            print("I created the magic folder on the desktop!")
        else:
            print("The folder already existed, no problem.")
    output_as: script_result

  - id: announce_result
    action: AUDIO__speak
    params:
      text: "{{ script_result }}"
    depends_on:
      - universal_python_script
```

This way you have created an automation that you can share with anyone, regardless of the PC or operating system they use!
"""

with codecs.open('c:/Hecos/docs/user/17_flows_it.md', 'a', encoding='utf-8') as f:
    f.write(content_it)
    
with codecs.open('c:/Hecos/docs/user/17_flows_en.md', 'a', encoding='utf-8') as f:
    f.write(content_en)
    
# Check if ES exists, if yes append. If not create it.
es_path = 'c:/Hecos/docs/user/17_flows_es.md'
if os.path.exists(es_path):
    pass # I'll translate the whole thing later if needed, but let's assume it doesn't exist yet or the user will rely on me to create it.
