from setuptools import setup, find_packages

setup(
    name='maintenance',
    version='1.0.0',
    description='A package that provides all maintenance tasks',
    author='Michał Moroz <michal@makimo.pl>',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
    ],
    packages=('maintenance',),
    package_dir={'': 'src'},
    install_requires=['docopt', 'daemonize', 'requests', 'psutil', 'redis'],
    python_requires='>=3',
    entry_points={
        'console_scripts': [
            'notify-on-exit = maintenance.tools.notify_on_exit:main',
            'notify-when-done = maintenance.tools.notify_when_done:main',
            'coordinate = maintenance.tools.coordinate:main',
        ],
    }
)
