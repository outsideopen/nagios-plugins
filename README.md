# Nagios Plugin Collection

Collection of Nagios Plugins

## check_aad_sync_status.py (DEPRECATED)

Used to check Azure AD Connect synchronization status from within Office 365. It reports on both DirSync and PasswordSync

NOTE: This no longer works with the new Office 365 login screen.

### Usage

- `./check_aad_sync_status.py -u username -p pasword`
- `./check_aad_sync_status.py -F /path/to/file.cred`

#### Credential File

The credential file is expected to be in the following format:

```
username = username
password = password
```

It is recommended to set the credential file to 600: `chmod 600 /path/to/file.cred`

## snmp_check_disk.py

**NOTE** Currently only supports SNMP v1

This works similarly to the Nagios check_disk plugin, but uses UCD SNMP on the host

## snmp_check_load.py

**NOTE** Currently only supports SNMP v1

This works similarly to the Nagios check_load plugin, but uses UCD SNMP on the host

## Other Projects

* https://github.com/waja/nagios-snmp-plugins
