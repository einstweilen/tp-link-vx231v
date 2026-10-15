"""
SNMP-v3-Parameter (USM) für die Net-SNMP-Kommandozeilenwerkzeuge.

Der Router wird weiterhin mit den Net-SNMP-Werkzeugen snmpget/snmpwalk
abgefragt, die per subprocess mit einer Argumentliste (ohne Shell) aufgerufen
werden. Das vermeidet Probleme mit Leerzeichen und Sonderzeichen in
Benutzername oder Passwort.

Statt SNMP v2c mit Community-String wird SNMP v3 mit Benutzer-
Authentifizierung verwendet. Voreinstellung wie im Router konfiguriert:
Sicherheitsstufe authNoPriv mit Authentifizierungsprotokoll MD5.
Die Zugangsdaten kommen ausschließlich aus der config.ini ([SNMP]),
niemals fest aus dem Code.

Hinweis: Die Passphrase steht in der Kommandozeile und ist damit für andere
Nutzer des Rechners sichtbar (ps). Alternative: ~/.snmp/snmp.conf mit
defSecurityName, defAuthType, defAuthPassphrase und defSecurityLevel.
"""

SECURITY_LEVELS = ('authNoPriv', 'authPriv', 'noAuthNoPriv')
AUTH_PROTOCOLS = ('MD5', 'SHA')
PRIV_PROTOCOLS = ('DES', 'AES')


class SnmpConfigError(RuntimeError):
    """Die SNMP-v3-Konfiguration fehlt oder ist widersprüchlich."""


class SnmpConfig:
    """Hält die SNMP-v3-Zugangsdaten und baut die Net-SNMP-Argumente."""

    def __init__(self, ip=None, user=None, password=None, auth='MD5',
                 level='authNoPriv', priv=None, priv_proto='DES'):
        self.ip = (ip or '').strip()
        self.user = (user or '').strip()
        self.password = password or ''
        self.auth = (auth or 'MD5').strip()
        self.level = (level or 'authNoPriv').strip()
        self.priv = priv or ''
        self.priv_proto = (priv_proto or 'DES').strip()

    @classmethod
    def from_config(cls, config, ip=None):
        """Liest die SNMP-v3-Werte aus der Config ([Router] und [SNMP])."""
        def get(option, fallback=''):
            if not config.has_section('SNMP'):
                return fallback
            return config.get('SNMP', option, fallback=fallback)

        if ip is None:
            ip = config.get('Router', 'routerip', fallback='')

        return cls(
            ip=ip,
            user=get('snmpuser'),
            password=get('snmppass'),
            auth=get('snmpauth', 'MD5'),
            level=get('snmplevel', 'authNoPriv'),
            priv=get('snmppriv'),
            priv_proto=get('snmpprivproto', 'DES'),
        )

    def missing(self):
        """Listet die fehlenden Pflichtangaben auf (leer = vollständig)."""
        names = (
            (self.ip, "Router-IP ('routerip' in [Router])"),
            (self.user, "SNMP-Benutzer ('snmpuser' in [SNMP])"),
            (self.password, "SNMP-Passwort ('snmppass' in [SNMP])"),
        )
        return [label for value, label in names if not value]

    def validate(self):
        """Prüft die Pflichtangaben und wirft bei Fehlern SnmpConfigError."""
        missing = self.missing()
        if missing:
            raise SnmpConfigError(
                "SNMP v3 ist unvollständig konfiguriert. Fehlend: "
                + ', '.join(missing)
                + ' in der config.ini.')

        if self.level not in SECURITY_LEVELS:
            raise SnmpConfigError(
                f"Ungültige Sicherheitsstufe 'snmplevel = {self.level}' "
                f"(erlaubt: {', '.join(SECURITY_LEVELS)}).")

        if self.level != 'noAuthNoPriv' and self.auth.upper() not in AUTH_PROTOCOLS:
            raise SnmpConfigError(
                f"Ungültiges Authentifizierungsprotokoll 'snmpauth = {self.auth}' "
                f"(erlaubt: {', '.join(AUTH_PROTOCOLS)}).")

        if self.level == 'authPriv':
            if not self.priv:
                raise SnmpConfigError(
                    "Sicherheitsstufe authPriv benötigt zusätzlich ein "
                    "Privacy-Passwort ('snmppriv' in [SNMP]).")
            if self.priv_proto.upper() not in PRIV_PROTOCOLS:
                raise SnmpConfigError(
                    f"Ungültiges Privacy-Protokoll 'snmpprivproto = {self.priv_proto}' "
                    f"(erlaubt: {', '.join(PRIV_PROTOCOLS)}).")

    def options(self):
        """Net-SNMP-Optionen der SNMP-v3-Anmeldung (ohne Ziel und OIDs)."""
        self.validate()
        opts = ['-v3', '-l', self.level, '-u', self.user]
        if self.level != 'noAuthNoPriv':
            opts += ['-a', self.auth.upper(), '-A', self.password]
        if self.level == 'authPriv':
            opts += ['-x', self.priv_proto.upper(), '-X', self.priv]
        return opts

    def argv(self, tool, *oids, output_opts=()):
        """Vollständiger Aufruf als Argumentliste, z. B.
        argv('snmpget', '1.3.6.1.2.1.1.1.0', output_opts=('-Ovq',))."""
        self.validate()
        return [tool, *self.options(), *output_opts, self.ip, *oids]
