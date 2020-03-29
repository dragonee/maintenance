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
    packages=('maintenance', 'maintenance.tools', 'maintenance.redis', 'maintenance.config', 'maintenance.services'),
    package_dir={'': 'src'},
    install_requires=['docopt', 'daemonize', 'requests', 'psutil', 'redis', 'selenium', 'fabric', 'pyserial'],
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
            'coordinate-arduino = maintenance.services.coordinate_arduino:main',
        ],
    }
)
