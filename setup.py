#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Setup script for BOT360

Install: pip install -e .
Build: python setup.py build
"""

from setuptools import setup, find_packages
import os

# Read long description from README
here = os.path.abspath(os.path.dirname(__file__))
try:
    with open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
        long_description = f.read()
except FileNotFoundError:
    long_description = 'Bot de Automatización INPEC'

setup(
    name='bot360',
    version='1.0.0',
    description='Bot de Automatización INPEC - Gestión de Agendas y Historias Clínicas',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Bot360 Team',
    author_email='team@bot360.local',
    url='https://github.com/tu-usuario/bot360',
    license='MIT',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    include_package_data=True,
    install_requires=[
        'flask==3.0.0',
        'selenium==4.15.2',
        'webdriver-manager==4.0.1',
        'pandas==2.1.4',
        'openpyxl==3.1.2',
        'requests==2.31.0',
        'pymupdf==1.23.8',
        'urllib3==2.1.0',
        'python-dotenv==1.0.0',
        'PyQt6==6.6.1',
    ],
    extras_require={
        'dev': [
            'pytest==7.4.3',
            'pytest-cov==4.1.0',
            'black==23.12.0',
            'flake8==6.1.0',
            'mypy==1.7.0',
        ],
        'build': [
            'pyinstaller==6.3.0',
            'pyinstaller-hooks-contrib==2023.11',
        ],
    },
    python_requires='>=3.9',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Operating System :: Windows',
    ],
    entry_points={
        'console_scripts': [
            'bot360-cli=bot360_app.web.server:main',
            'bot360-gui=ui.desktop_app:main',
        ],
    },
)
