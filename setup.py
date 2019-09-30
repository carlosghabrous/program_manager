import setuptools

with open("README.md", "r") as fh:
	description = fh.read()

setuptools.setup(
  name             = "program_manager",
  version          = "1.0.0",
  author           = "Carlos Ghabrous Larrea",
  author_email     = "carlos.ghabrous@cern.ch",
  description      = description,
  url              = "https://gitlab.cern.ch/ccs/fgc/tree/master/sw/clients/python/program_manager",
  python_requires  = ">=3.6",
  install_requires = ["pyfgc>=1.1", "pyfgc_statussrv>=1.0", "docopt>=0.6", "termcolor>=1.1"],
  packages         = setuptools.find_packages(),
  data_files       = [("program_manager", ["data/pm_config.cfg"])]
)
