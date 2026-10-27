#!/usr/bin/env python3
"""Compatibilidad del arranque anterior; el backend ahora es Django."""
import argparse
import os
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=int(os.getenv('PORT', '8000')))
    parser.add_argument('--host', type=str, default=os.getenv('HOST', '0.0.0.0'))
    parser.add_argument('--init-db', action='store_true', help='Crear tablas Django sin importar datos')
    args = parser.parse_args()
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sgr.settings')
    from django.core.management import execute_from_command_line
    if args.init_db:
        execute_from_command_line([sys.argv[0], 'migrate'])
    else:
        execute_from_command_line([sys.argv[0], 'runserver', f'{args.host}:{args.port}', '--noreload'])


if __name__ == '__main__':
    main()
