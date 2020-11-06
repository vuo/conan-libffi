from conans import ConanFile, tools, AutoToolsBuildEnvironment
import os
import platform

class LibffiConan(ConanFile):
    name = 'libffi'

    source_version = '3.4pre'
    package_version = '0'
    version = '%s-%s' % (source_version, package_version)

    build_requires = (
        'llvm/5.0.2-1@vuo/stable',
        'macos-sdk/11.0-0@vuo/stable',
    )
    settings = 'os', 'compiler', 'build_type', 'arch'
    url = 'https://github.com/libffi/libffi'
    license = 'https://github.com/libffi/libffi/blob/master/LICENSE'
    description = 'A portable, high level programming interface to various calling conventions'
    source_dir = 'libffi'

    build_x86_dir = '_build_x86'
    build_arm_dir = '_build_arm'
    install_x86_dir = '_install_x86'
    install_arm_dir = '_install_arm'
    install_universal_dir = '_install_universal_dir'

    exports_sources = '*.patch'

    def source(self):
        self.run("git clone https://github.com/libffi/libffi.git")
        with tools.chdir(self.source_dir):
            # The commit that the arm64 patch below was based on.
            self.run("git checkout  ead65ca")

            # https://github.com/libffi/libffi/pull/565
            tools.patch(patch_file='../arm64.patch')

            self.run("./autogen.sh")

        self.run('mv %s/LICENSE %s/%s.txt' % (self.source_dir, self.source_dir, self.name))

    def build(self):
        autotools = AutoToolsBuildEnvironment(self)

        # The LLVM/Clang libs get automatically added by the `requires` line,
        # but this package doesn't need to link with them.
        autotools.libs = []

        autotools.flags.append('-Oz')

        if platform.system() == 'Darwin':
            autotools.flags.append('-isysroot %s' % self.deps_cpp_info['macos-sdk'].rootpath)
            autotools.flags.append('-mmacosx-version-min=10.11')
            autotools.link_flags.append('-Wl,-install_name,@rpath/libffi.dylib')

        common_configure_args = [
            '--quiet',
            '--disable-debug',
            '--disable-dependency-tracking',
            '--disable-docs',
            '--disable-multi-os-directory',
            '--disable-static',
            '--enable-shared',
        ]

        env_vars = {
            'CC' : self.deps_cpp_info['llvm'].rootpath + '/bin/clang',
            'CXX': self.deps_cpp_info['llvm'].rootpath + '/bin/clang++',
        }
        with tools.environment_append(env_vars):
            build_root = os.getcwd()

            self.output.info("=== Build for x86_64 ===")
            tools.mkdir(self.build_x86_dir)
            with tools.chdir(self.build_x86_dir):
                autotools.flags.append('-arch x86_64')
                autotools.link_flags.append('-arch x86_64')
                autotools.configure(configure_dir='../%s' % self.source_dir,
                                    build=False,
                                    host=False,
                                    args=common_configure_args + [
                                        '--prefix=%s/%s' % (build_root, self.install_x86_dir),
                                    ])
                autotools.make(args=['--quiet'])
                autotools.make(target='install', args=['--quiet'])

            self.output.info("=== Build for arm64 ===")
            tools.mkdir(self.build_arm_dir)
            with tools.chdir(self.build_arm_dir):
                autotools.flags.remove('-arch x86_64')
                autotools.flags.append('-arch arm64')
                autotools.link_flags.remove('-arch x86_64')
                autotools.link_flags.append('-arch arm64')
                autotools.configure(configure_dir='../%s' % self.source_dir,
                                    build=False,
                                    host=False,
                                    args=common_configure_args + [
                                        '--prefix=%s/%s' % (build_root, self.install_arm_dir),
                                        '--host=arm64-apple-darwin15.0.0',
                                    ])
                autotools.make(args=['--quiet'])
                autotools.make(target='install', args=['--quiet'])

    def package(self):
        if platform.system() == 'Darwin':
            libext = 'dylib'
        elif platform.system() == 'Linux':
            libext = 'so'
        else:
            raise Exception('Unknown platform "%s"' % platform.system())

        tools.mkdir(self.install_universal_dir)
        with tools.chdir(self.install_universal_dir):
            self.run('lipo -create ../%s/lib/libffi.%s ../%s/lib/libffi.%s -output libffi.%s' % (self.install_x86_dir, libext, self.install_arm_dir, libext, libext))

        self.copy('*.h', src='%s/include' % self.install_x86_dir, dst='include')
        self.copy('libffi.%s' % libext, src=self.install_universal_dir, dst='lib')
        self.copy(pattern='*.pc', dst='', keep_path=False)

        self.copy('%s.txt' % self.name, src=self.source_dir, dst='license')

    def package_info(self):
        self.cpp_info.libs = ['ffi']
