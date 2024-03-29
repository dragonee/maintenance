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
    packages=('maintenance', 'maintenance.tools', 'maintenance.redis', 'maintenance.config', 'maintenance.services', 'maintenance.archive'),
    package_dir={'': 'src'},
    install_requires=['docopt', 'daemonize', 'requests', 'psutil', 'redis', 'selenium', 'fabric', 'pyserial', 'environs', 'mysql-connector-python'],
    python_requires='>=3',
    entry_points={
        'console_scripts': [
            'notify-on-exit = maintenance.tools.notify_on_exit:main',
            'notify-when-done = maintenance.tools.notify_when_done:main',
            'coordinate = maintenance.tools.coordinate:main',
            'yt-remove-watchlater = maintenance.tools.remove_youtube_watchlater:main',
            'yt-download-watch-later = maintenance.tools.youtube_pipeline:main',
            'video-feed = maintenance.tools.video_feed:main',
            'video-lengths = maintenance.tools.video_lengths:main',
            'arduino = maintenance.tools.arduino:main',
            'coordinate-arduino = maintenance.services.coordinate_arduino:main',
            'eternalize = maintenance.tools.eternalize:main',
            'eternalize-locate = maintenance.tools.eternalize_locate:main',
            'eternalize-resolve-conflict = maintenance.tools.eternalize_resolve_conflict:main',
            'make-readme = maintenance.tools.make_readme:main',
            'markdown-command = maintenance.tools.markdown_command:main',
            'archive-mysql = maintenance.tools.archive_mysql:main',
            'archive-pgsql = maintenance.tools.archive_pgsql:main',
            'archive-pack-wordpress = maintenance.tools.archive_pack_wordpress:main',
            'archive-pack-bedrock = maintenance.tools.archive_pack_bedrock:main',
            'archive-pack-generic = maintenance.tools.archive_pack_generic:main',
            'archive-teardown-mysql = maintenance.tools.archive_teardown_mysql:main',
            'archive-compress = maintenance.tools.archive_compress:main',
            'archive-check = maintenance.tools.archive_check:main',
            'archive-store-ssh = maintenance.tools.archive_store_ssh:main',
            'archive = maintenance.tools.archive:main',
        ],
    }
)
