# Discord Moderation Bot

Un bot di moderazione Discord completo e professionale costruito in Python con slash commands, auto-moderazione e logging dettagliato.

## Caratteristiche

### 🛡️ Moderazione Completa
- **Ban/Unban** - Con supporto per ban temporanei
- **Kick** - Rimozione immediata dal server
- **Timeout** - Silenziamento temporaneo automatico
- **Warn/Unwarn** - Sistema di avvertimenti con auto-punizione
- **Purge** - Eliminazione messaggi in massa

### 🤖 Auto-Moderazione
- **Anti-Spam** - Rilevamento messaggi rapidi
- **Anti-Caps** - Controllo maiuscole eccessive
- **Filtro Parole** - Lista personalizzabile parole vietate
- **Anti-Invite** - Blocco link di invito Discord
- **Testi Ripetuti** - Rilevamento contenuti duplicati

### 📊 Logging Completo
- **Eventi Messaggi** - Modifiche ed eliminazioni
- **Eventi Membri** - Entrate, uscite, ban, unban
- **Eventi Server** - Ruoli, canali, stati vocali
- **Log Staff** - Tracciamento comandi moderatori
- **Log Auto-Mod** - Violazioni automatiche

### 💾 Database SQLite
- **Cronologia Utenti** - Storia moderazione completa
- **Avvertimenti Attivi** - Gestione warn persistenti
- **Azioni Temporanee** - Auto-rimozione scadenze
- **Backup Automatici** - Protezione dati
- **Pulizia Automatica** - Gestione spazio storage

### 🔐 Sistema Permessi
- **Ruoli Gerarchici** - Admin, Moderatori, Helper
- **Controllo Comandi** - Accesso basato su ruoli
- **Controllo Gerarchia** - Protezione ruoli superiori

## Setup Rapido

### 1. Configurazione Bot Discord
1. Vai su https://discord.com/developers/applications
2. Crea una nuova applicazione
3. Vai alla sezione "Bot"
4. Copia il token del bot
5. Invita il bot nel server con permessi amministratore

### 2. Configurazione Server
1. Aggiungi il token come variabile d'ambiente `DISCORD_BOT_TOKEN`
2. Esegui `/setup` nel server per inizializzare
3. Configura i ruoli con `/config roles`
4. Personalizza le impostazioni in `config.yml`

## Comandi Disponibili

### Moderazione
- `/ban <user> [reason] [duration] [delete_messages]` - Banna un utente
- `/unban <user> [reason]` - Rimuove ban
- `/kick <user> [reason]` - Espelle utente
- `/timeout <user> [duration] [reason]` - Silenzia temporaneamente
- `/untimeout <user> [reason]` - Rimuove silenzio
- `/warn <user> <reason>` - Avverte utente
- `/unwarn <user> [reason]` - Rimuove avvertimento
- `/purge <amount> [user] [reason]` - Elimina messaggi

### Cronologia e Log
- `/history <user> [limit]` - Cronologia moderazione
- `/fullhistory <user>` - Cronologia completa paginata
- `/warnings <user>` - Avvertimenti attivi
- `/stafflogs [staff] [limit]` - Log comandi staff
- `/automodlogs [user] [type] [limit]` - Log auto-moderazione

### Amministrazione
- `/setup` - Configura bot per il server
- `/config <setting> [action]` - Gestisci impostazioni
- `/backup` - Backup database
- `/cleanup [days]` - Pulizia dati vecchi
- `/reload` - Ricarica configurazione
- `/stats` - Statistiche bot
- `/lock [channel] [reason]` - Blocca canale
- `/unlock [channel] [reason]` - Sblocca canale

### Utilità
- `/help [command]` - Guida comandi

## Configurazione

### config.yml
Configurazione principale del bot con impostazioni per:
- Prefisso e stato bot
- Limiti avvertimenti e auto-punizione
- Soglie auto-moderazione
- Canali e ruoli permessi
- Colori embed personalizzati

### messages.yml
Messaggi personalizzabili per:
- Risposte comandi
- Notifiche DM punizioni
- Log eventi server
- Messaggi auto-moderazione
- Errori e successi

## Struttura Database

Il bot utilizza SQLite con le seguenti tabelle:
- `warnings` - Avvertimenti utenti
- `mod_history` - Cronologia moderazione
- `guild_settings` - Impostazioni server
- `message_logs` - Log messaggi
- `staff_logs` - Log comandi staff
- `temp_actions` - Azioni temporanee
- `automod_violations` - Violazioni auto-mod

## Auto-Moderazione

### Configurazione Spam
```yaml
spam:
  enabled: true
  max_messages: 5
  time_window: 10
  punishment: "timeout"
  duration: 600
```

### Configurazione Caps
```yaml
caps:
  enabled: true
  threshold: 0.7
  min_length: 10
  punishment: "warn"
```

### Filtro Parole
```yaml
bad_words:
  enabled: true
  punishment: "warn"
  words: 
    - "parola_esempio"
```

## Logging Eventi

Il bot registra automaticamente:
- **Messaggi** - Eliminazioni e modifiche
- **Membri** - Join, leave, ban, unban
- **Ruoli** - Creazione, eliminazione, modifiche
- **Canali** - Creazione, eliminazione, modifiche
- **Voce** - Entrate/uscite canali vocali
- **Moderazione** - Tutte le azioni staff

## Permessi Richiesti

Il bot necessita dei seguenti permessi Discord:
- Gestisci Messaggi
- Gestisci Ruoli
- Gestisci Canali
- Banna Membri
- Espelli Membri
- Modera Membri (Timeout)
- Leggi Cronologia Messaggi
- Invia Messaggi
- Incorpora Link
- Usa Comandi Slash

## Sicurezza

- **Controllo Gerarchia** - Impedisce azioni su ruoli superiori
- **Log Completo** - Tracciabilità tutte le azioni
- **Backup Automatici** - Protezione perdita dati
- **Permessi Granulari** - Controllo accesso preciso
- **Rate Limiting** - Protezione spam comandi

## Supporto e Manutenzione

- **Backup Database** - `/backup` per sicurezza dati
- **Pulizia Automatica** - `/cleanup` per gestione spazio
- **Reload Config** - `/reload` per aggiornamenti live
- **Statistiche** - `/stats` per monitoraggio uso
- **Log Dettagliati** - File `bot.log` per debugging

## File Principali

- `main.py` - Entry point e configurazione bot
- `config.yml` - Configurazione principale
- `messages.yml` - Messaggi personalizzati
- `cogs/` - Moduli funzionalità
- `utils/` - Utilities e helper
- `database.db` - Database SQLite

Il bot è completamente configurabile, scalabile e pronto per la produzione con funzionalità professionali di moderazione Discord.