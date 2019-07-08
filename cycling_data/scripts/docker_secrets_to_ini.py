def main():
    tpl=open('production.ini.tpl').read()
    with open('production.ini','w') as fh_ini:
        subs={}
        for secret_name in 'mysql_root_password','mysql_production_password','cycling_admin_password','pyramid_auth_secret':
            with open(secret_name) as fh_secret:
                subs[secret_name]=fh_secret.read()
        fh_ini.write(tpl.format(**subs))
