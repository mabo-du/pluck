# SPDX-License-Identifier: MIT
# Homebrew formula for pluck — install from any git forge
#
# Install with:
#   brew install --formula HomebrewFormula/pluck-cli.rb

class PluckCli < Formula
  include Language::Python::Virtualenv

  desc "Pluck git repos from any forge — auto-detect, auto-install, done!"
  homepage "https://gitlab.com/mabodu/pluck"
  url "https://files.pythonhosted.org/packages/source/p/pluck-cli/pluck_cli-0.2.0.tar.gz"
  license "MIT"

  depends_on "python@3.12"

  def install
    virtualenv_install_with_resources
  end

  test do
    system "#{bin}/pluck", "version"
  end
end
