from pythonforandroid.recipe import PythonRecipe


class YtDlpRecipe(PythonRecipe):
    version = '2023.12.30'
    url = 'https://github.com/yt-dlp/yt-dlp/archive/refs/tags/{version}.tar.gz'
    depends = ['setuptools', 'pycryptodomex', 'websockets', 'brotli', 'mutagen', 'certifi']
    site_packages_name = 'yt_dlp'
    call_hostpython_via_targetpython = False
    
    def prebuild_arch(self, arch):
        super().prebuild_arch(arch)
        # Patch for Android compatibility if needed
        pass


recipe = YtDlpRecipe()
