# Copyright (C) 2013-2014 Alexander Weigl
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see http://www.gnu.org/licenses/>.

from __future__ import print_function

"""hf3lint -- Module provides an linter/checker for hf3 and bcdata files.

This module provides function to validate hf3 and bcdata files.


"""

__author__ = "Alexander Weigl uiduw@student.kit.edu>"
__date__ = "2014-08-27"
__version__ = "0.1-rc"

import re

REGEX_NATURAL = re.compile(r'^\d+$')
REGEX_INTEGER = re.compile(r'^[+-]?\d+$')
REGEX_FLOAT = re.compile(r'^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$')


class Entry(object):
    """Report entry generated by a linter.
    """

    def __init__(self, level, message, path):
        self.level = level
        self.message = message
        self.path = path
        self.number = 0


def getter(path):
    """Returns a function that access the given path in a dictionary.

    :param path: a string with period seperated segements, like "a.b.c." for accessing d['a']['b']['c'].
                Or a sequence like ['a','b','c']
    :type path: str or list
    :return: a function `fn(o)` with `getter("p.q.r.s")(o) == o[p][q][r][s]`
    """

    def fn(data):
        segments = path.split(".") if isinstance(path, str) else path
        for s in segments:
            data = data.get(s, None)
            if data is None:
                break
        return data

    return fn


def get(path, data):
    """Access the given path in the dictionary `data`
    :param path:
    :type path: str or sequence
    :param data:
    :type data: dict[str,object]
    :return: object or None
    """
    return getter(path)(data)


class _RuleDispatcher(object):
    """Base class for linter.

    Calls every `_rule_*` method within this class.
    So a rule should begin with `_rule_` and accept one dictionary argument.
    Check results should be gathered with `self.add_*` functions.

    """

    def __init__(self):
        self._report = []

    def add_error(self, message, path):
        self._report.append(Entry('E', message, path))

    def add_warning(self, message, path):
        self._report.append(Entry('W', message, path))

    def add_information(self, message, path):
        self._report.append(Entry('I', message, path))

    def assert_error(self, condition, message, path):
        if not condition:
            self.add_error(message, path)
        return condition

    def assert_warning(self, condition, message, path):
        if not condition:
            self.add_warning(message, path)
        return condition

    def validate(self, data):
        rule_filter = lambda x: x.startswith("_rule_")
        rules = sorted(filter(rule_filter, dir(self)))

        self._report = []
        for r in rules:
            getattr(self, r)(data)
        return self._report


from functools import partial


class Checkers(object):
    """Just a bunch of check functions.

    A check functions should return two values `(a,b)`:

    `a` -- True or False, True iff. the check is negative (no error) resp. False
    `b` -- The message for the linter, only taken if `a` is False.

    """

    @staticmethod
    def is_str(o):
        t = o is not None and isinstance(o, str)
        return t, "string expected"


    @staticmethod
    def file_exists(o):
        import os.path

        t = os.path.exists(o)
        return t, "file %s does exists" % (os.path.abspath(o))

    @staticmethod
    def is_regex(regex, o):
        t = regex.match(o)
        return t, "field '%s' was not matched by %s " % (o.strip(), regex.pattern)

    @staticmethod
    def is_natural_number(o):
        return Checkers.is_regex(REGEX_NATURAL, o)

    @staticmethod
    def is_float(o):
        return Checkers.is_regex(REGEX_FLOAT, o)

    @staticmethod
    def oneOf(*args):
        return partial(Checkers.isOneOf, set(args))

    @staticmethod
    def isOneOf(enum, o):
        return o in enum, "%s has to be in %s" % (o, enum)

    @staticmethod
    def is_int(o):
        return Checkers.is_regex(REGEX_INTEGER, o)

    @staticmethod
    def is_equals(a, b):
        return str(a) == b, "%s is not equals %s" % (str(a), b)


class HF3DataLint(_RuleDispatcher):
    FIELDS = {
        'Param': {
            'OutputPathAndPrefix': Checkers.is_str,

            'Mesh': {
                'Filename': Checkers.file_exists,
                'BCdataFilename': Checkers.file_exists,
                'InitialRefLevel': Checkers.is_natural_number,
            },

            'LinearAlgebra': {
                'Platform': Checkers.oneOf('CPU', 'GPU', 'OPENCL'),
                'Implementation': Checkers.oneOf('Naive', 'BLAS', 'OPENMP', 'MKL'),
                'MatrixFormat': Checkers.oneOf('NAIVE', 'BLAS', 'COO', 'ELL', 'CSR'),
            },

            'ElasticityModel': {
                'density': Checkers.is_float,
                'lambda': Checkers.is_natural_number,
                'mu': Checkers.is_natural_number,
                'gravity': Checkers.is_float,
            },

            'QuadratureOrder': 2,

            'FiniteElements': {
                'DisplacementDegree': 1
            },

            'Instationary': {
                'SolveInstationary': Checkers.oneOf('1', '2'),
                'DampingFactor': 1.0,
                'RayleighAlpha': Checkers.is_float,
                'RayleighBeta': Checkers.is_float,
                'Method': Checkers.oneOf('ImplicitEuler', 'CrankNicolson', 'ExplicitEuler', 'Newmark'),
                'DeltaT': Checkers.is_float,
                'MaxTimeStepIts': Checkers.is_natural_number,
            },

            'Boundary': {
                'DirichletMaterial1': Checkers.is_natural_number,
                'DirichletMaterial2': Checkers.is_natural_number,
                'DirichletMaterial3': Checkers.is_natural_number,
                'NeumannMaterial1': Checkers.is_natural_number,
                'NeumannMaterial1Pressure': Checkers.is_float,
                'NeumannMaterial2': Checkers.is_natural_number,
                'NeumannMaterial2Pressure': Checkers.is_float,
            },

            'LinearSolver': {
                'SolverName': Checkers.oneOf('CG', 'GMRES'),
                'MaximumIterations': Checkers.is_natural_number,
                'AbsoluteTolerance': Checkers.is_float,
                'RelativeTolerance': Checkers.is_float,
                'DivergenceLimit': Checkers.is_float,
                'BasisSize': Checkers.is_natural_number,
                'Preconditioning': Checkers.oneOf('0', '1'),
                'PreconditionerName': Checkers.oneOf('SGAUSS_SEIDEL', 'NOPRECOND', 'JACOBI', 'GAUSS_SEIDEL',
                                                     'SGAUSS_SEIDEL', 'SOR', 'SSOR', 'ILU', 'ILU2', 'ILU_P', 'ILUpp'),
                'Omega': Checkers.is_float,
                'ILU_p': Checkers.is_float,
            },
            'ILUPP': {
                'PreprocessingType': 0,
                'PreconditionerNumber': 11,
                'MaxMultilevels': 20,
                'MemFactor': 0.8,
                'PivotThreshold': 2.75,
                'MinPivot': 0.05,
            }
        }
    }

    @staticmethod
    def _build_rules_from_fields():
        def recur(d, path, result):
            for k, v in d.iteritems():
                np = path + [k]
                if isinstance(v, dict):
                    recur(v, np, result)

                elif callable(v):
                    result.append((np, v))

                else:
                    fn = partial(Checkers.is_equals, v)
                    result.append((np, fn))

        r = []
        recur(HF3DataLint.FIELDS, [], r)
        return r

    def _rule_check_FIELDS(self, data):
        for path, fn in HF3DataLint._build_rules_from_fields():
            value = get(path, data)
            p = '.'.join(path)
            if value is None:
                self.add_error("Field does not exists", p)
            else:
                check, message = fn(value)
                self.assert_error(check, message, p)


    def _rule_lambda_mu(self, data):
        a_mu = "Param.ElasticityModel.mu"
        a_lambda = "Param.ElasticityModel.lambda"

        mu = float(get(a_mu, data))
        lam = float(get(a_lambda, data))

        t = mu <= 0.5 * lam

        self.assert_warning(t, "%s should half so small or smaller than %s" % (a_mu, a_lambda), a_mu)


class BCDataLint(_RuleDispatcher):
    def _check_points_format(self, path, points):
        for vector in points.split(";"):
            nums = vector.split(",")
            if len(nums) != 3:
                self.add_error("The vector %s does not have exact 3 components" %
                               vector, path)

            for n in nums:
                # print("'",n,"'")
                t, msg = Checkers.is_float(n)
                self.assert_error(t, msg, path)

    def _check_exists(self, data, path, prefixpath=None):
        t = get(path, data) is not None
        self.assert_error(
            t,
            "Field does not exists",
            (prefixpath + "." if prefixpath else "") + path)
        return t

    def _rule_FixedConstraintsBCs(self, data):
        rootpath = "Param.BCData.FixedConstraintsBCs"
        NumberOfFixedDirichletPoints = "NumberOfFixedDirichletPoints"
        fDPoints = "fDPoints"
        fDisplacements = "fDisplacements"
        self._check_entry(data, rootpath, NumberOfFixedDirichletPoints,
                          fDPoints, fDisplacements)

    def _rule_DisplacementConstraintsBCs(self, data):
        rootpath = "Param.BCData.DisplacementConstraintsBCs"
        NumberOfDisplacedDirichletPoints = "NumberOfDisplacedDirichletPoints"
        dDisplacements = "dDisplacements"
        dDPoints = "dDPoints"
        self._check_entry(data, rootpath, NumberOfDisplacedDirichletPoints,
                          dDPoints, dDisplacements)

    def _rule_ForceOrPressureBCs(self, data):
        rootpath = "Param.BCData.ForceOrPressureBCs"
        NumberOfForceOrPressureBCPoints = "NumberOfForceOrPressureBCPoints"
        ForcesOrPressure = "ForcesOrPressure"
        ForceOrPressureBCPoints = "ForceOrPressureBCPoints"
        self._check_entry(data, rootpath, NumberOfForceOrPressureBCPoints,
                          ForceOrPressureBCPoints, ForcesOrPressure)

    def _check_entry(self, data, rootpath, numberOf, points, displacement):
        struct = get(rootpath, data)

        if struct is None:  # struct is allowed to be missed
            return


        # all three childs have to be there
        all_exists = \
            self._check_exists(struct, numberOf, rootpath) and \
            self._check_exists(struct, points, rootpath) and \
            self._check_exists(struct, displacement, rootpath)

        # if one missing abort
        if not all_exists:
            return

        # check if # of point is number
        t, msg = Checkers.is_natural_number(get(numberOf, struct))
        number = self.assert_error(t, msg, rootpath + "." + numberOf)

        # abort if number is not a number
        if not t:
            return

        def check_points(field):
            exp = int(get(numberOf, struct))
            found = 1 + get(field, struct).count(";")
            self.assert_error(
                exp == found,
                "Amount of points mismatch (expected %s, found %s)" % (exp, found),
                rootpath + "." + field
            )

        check_points(points)
        check_points(displacement)

        self._check_points_format(
            rootpath + "." + displacement,
            get(displacement, struct))

        self._check_points_format(
            rootpath + "." + points,
            get(points, struct))


def dictionfy(tree):
    """Creates a dictionary structure from a simple xml tree.

    :param tree: lxml.etree._Element
    :rtype: dict
    """
    if tree.text is not None:
        return {tree.tag: tree.text}
    else:
        d = {}
        for child in tree.iterchildren():
            v = dictionfy(child).values()[0]
            d[child.tag] = v
        return {tree.tag: d}


def read_xml(filename):
    """Reads an xml file
    :param filename: path to a xml file
    :type filename: str
    :returns: a dict structure
    :rtype: dict
    """
    import lxml.etree

    with open(filename) as fp:
        parser = lxml.etree.XMLParser(remove_blank_text=True,
                                      remove_pis=True,
                                      remove_comments=True)
        tree = lxml.etree.parse(fp, parser=parser)
        return dictionfy(tree.getroot())


class ReportPrinter(object):
    def __init__(self):
        pass

    _COLOR_TABLE = {'H': 94, 'W': 33, 'E': 31, 'D': 90}
    """Report type to terminal color table"""

    _COLOR_FORMAT = "{color}{type}-{number}: {msg} {grey}{path}{nocolor}"
    """format of terminal output"""

    _TERM_FORMAT = "{type}-{number}: {msg} in {path}"
    """format of terminal output"""


    def __call__(self, format, report, **kwargs):
        """Print the report

        :param errors:  display errors 
        :param warnings:  display warnings
        :param hints: display hints
        :param report: list of Entry
        :return: None
        :rtype: None
        """
        print_func = getattr(self, "_print_%s" % format)
        print_func(report, **kwargs)

    def _print_term(self, report, errors=True, warnings=True, hints=True):
        for r in report:
            print(ReportPrinter._TERM_FORMAT.format(
                type=r.level,
                number=r.number,
                msg=r.message,
                path=r.path
            ))

    def _print_cterm(self, report, errors=True, warnings=True, hints=True):
        for r in report:
            color = ReportPrinter._COLOR_TABLE.get(r.level, 33)
            print(ReportPrinter._COLOR_FORMAT.format(
                type=r.level,
                number=r.number,
                msg=r.message,
                color="\x1b[%dm" % color,
                nocolor="\x1b[0m",
                grey="\x1b[37m",
                path=r.path
            ))

    def _print_json(self, report, errors=True, warnings=True, hints=True):
        import json
        print(json.dumps(report))

    def _print_xml(self, report, errors=True, warnings=True, hints=True):

        import lxml.etree

        root = lxml.etree.Element("report")

        for r in report:
            entry = lxml.etree.SubElement(root, "entry")
            entry.attrib["level"] = r.level
            entry.attrib["number"] = str(r.number)
            entry.attrib["message"] = r.message
            entry.attrib["path"] = r.path

        print(lxml.etree.tostring(root, encoding="utf-8", pretty_print=True, standalone=True))

    def _print_csv(self, report, errors=True, warnings=True, hints=True, delimiter="\t"):
        import csv, sys

        w = csv.writer(sys.stdout)

        for r in report:
            w.writerow([r.level, r.number, r.message, r.path])


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--language", type=str,
                        help="defines the linter: one of hf3, bc, auto",
                        choices=['hf3', 'bc', 'auto'],
                        default="auto")

    parser.add_argument("-f", "--format", type=str,
                        choices=['json', 'xml', 'csv', 'term', 'cterm'],
                        default="cterm",
                        help="output format of messages", )

    def add_onoff(char, help, dest):
        parser.add_argument("-%s" % char.upper(), help="deactivate %s" % dest,
                            action="store_false", dest=dest)

        parser.add_argument("-%s" % char.lower(), help="activate %s" % dest,
                            action="store_true", dest=dest)

    add_onoff("e", "active/deactive error", "errors")
    add_onoff("w", "active/deactive error", "warnings")
    add_onoff("i", "active/deactive error", "hints")

    parser.add_argument("file", help="file to be checked")
    options = parser.parse_args()

    language = options.language
    errors = options.errors
    warnings = options.warnings
    hints = options.hints

    format = options.format
    file = options.file

    report = lint(language, file)

    p = ReportPrinter()

    p(format, report,
      errors=options.errors,
      warnings=options.warnings,
      hints=options.hints)


def lint(language, file):
    content = read_xml(file)

    if language == 'auto':
        language = language_auto_detect(content)

    print(language)
    if language == 'bc':
        checker = BCDataLint()

    if language == 'hf3':
        checker = HF3DataLint()

    return checker.validate(content)


def language_auto_detect(content):
    if 'BCData' in content['Param']:
        return "bc"

    if 'Mesh' in content['Param']:
        return 'hf3'


if __name__ == "__main__":
    main()
    
