from conans import ConanFile

class LibffiTestConan(ConanFile):
    generators = 'qbs'

    def build(self):
        self.run('qbs -f "%s"' % self.source_folder)

    def imports(self):
        self.copy('*.dylib', dst='bin', src='lib')

    def test(self):
        self.run('qbs run')

        # Ensure we only link to system libraries.
        self.run('! (otool -L bin/libffi.dylib | tail +3 | egrep -v "^\s*(/usr/lib/|/System/)")')
        self.run('! (otool -l lib/libffi.dylib | grep -A2 LC_RPATH | cut -d"(" -f1 | grep "\s*path" | egrep -v "^\s*path @(executable|loader)_path")')
