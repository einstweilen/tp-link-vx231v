# Lokalisierung und eigene Feldbeschriftungen

Die Datenbank `router_lang.db` dient als Übersetzungsmatrix. Sie wandelt technische Spaltennamen (z. B. `downstream_curr_rate`) für das Browser-Dashboard und den HTML-Bericht in menschenlesbare Bezeichner (z. B. "Aktuelle Download-Rate") um.<br>
Eigene Übersetzungen können direkt in der router_lang.db oder auch  im Quellcode des beiliegenden Hilfsskripts `lang_editor.py` (innerhalb der Liste `translations`) angepasst und erweitert werden. Ein anschließendes Ausführen des Skripts generiert die Übersetzungsdatenbank neu.
