PRAGMA foreign_keys = ON;

-- En rad per häst i aktuell avdelning (från v85_*.csv)
CREATE TABLE IF NOT EXISTS v85 (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  datum TEXT,
  avd TEXT,
  startnummer TEXT,
  hastnamn TEXT,
  kusk TEXT,
  tranare TEXT,
  v85_procent TEXT,
  v_odds TEXT,
  vagn TEXT,
  source_file TEXT,
  imported_at TEXT DEFAULT (datetime('now'))
);

-- Historikrader per häst (från v85_history_*.csv)
CREATE TABLE IF NOT EXISTS v85_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  datum TEXT,
  avd TEXT,
  hastnamn TEXT,
  bana TEXT,
  kusk TEXT,
  placering TEXT,
  distans_spor TEXT,
  km_tid TEXT,
  skor TEXT,
  odds TEXT,
  pris TEXT,
  vagn TEXT,
  source_file TEXT,
  imported_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_v85_hastnamn ON v85(hastnamn);
CREATE INDEX IF NOT EXISTS idx_v85_datum ON v85(datum);
CREATE UNIQUE INDEX IF NOT EXISTS uidx_v85_match ON v85(datum, avd, hastnamn);
CREATE INDEX IF NOT EXISTS idx_v85_history_hastnamn ON v85_history(hastnamn);
CREATE INDEX IF NOT EXISTS idx_v85_history_datum ON v85_history(datum);
CREATE INDEX IF NOT EXISTS idx_v85_history_match ON v85_history(datum, avd, hastnamn);
