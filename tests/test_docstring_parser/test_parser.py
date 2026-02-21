"""Tests for generic docstring routines."""

import re
from unittest.mock import patch

import pytest

from pymend.docstring_parser import base_parser
from pymend.docstring_parser.base_parser import compose, parse, rest
from pymend.docstring_parser.common import Docstring, DocstringStyle, ParseError


def test_rest() -> None:
    """Test ReST-style parser autodetection."""
    docstring = parse(
        """
        Short description

        Long description

        Causing people to indent:

            A lot sometimes

        :param spam: spam desc
        :param int bla: bla desc
        :param str yay:
        :raises ValueError: exc desc
        :returns tuple: ret desc
        """
    )

    assert docstring.style == DocstringStyle.REST
    assert docstring.short_description == "Short description"
    assert docstring.long_description == (
        "Long description\n\nCausing people to indent:\n\n    A lot sometimes"
    )
    assert len(docstring.params) == 3
    assert docstring.params[0].arg_name == "spam"
    assert docstring.params[0].type_name is None
    assert docstring.params[0].description == "spam desc"
    assert docstring.params[1].arg_name == "bla"
    assert docstring.params[1].type_name == "int"
    assert docstring.params[1].description == "bla desc"
    assert docstring.params[2].arg_name == "yay"
    assert docstring.params[2].type_name == "str"
    assert docstring.params[2].description == ""
    assert len(docstring.raises) == 1
    assert docstring.raises[0].type_name == "ValueError"
    assert docstring.raises[0].description == "exc desc"
    assert docstring.returns is not None
    assert docstring.returns.type_name == "tuple"
    assert docstring.returns.description == "ret desc"
    assert docstring.many_returns is not None
    assert len(docstring.many_returns) == 1
    assert docstring.many_returns[0] == docstring.returns


def test_google() -> None:
    """Test Google-style parser autodetection."""
    docstring = parse(
        """Short description

        Long description

        Causing people to indent:

            A lot sometimes

        Args:
            spam: spam desc
            bla (int): bla desc
            yay (str):

        Raises:
            ValueError: exc desc

        Returns:
            tuple: ret desc
        """
    )

    assert docstring.style == DocstringStyle.GOOGLE
    assert docstring.short_description == "Short description"
    assert docstring.long_description == (
        "Long description\n\nCausing people to indent:\n\n    A lot sometimes"
    )
    assert len(docstring.params) == 3
    assert docstring.params[0].arg_name == "spam"
    assert docstring.params[0].type_name is None
    assert docstring.params[0].description == "spam desc"
    assert docstring.params[1].arg_name == "bla"
    assert docstring.params[1].type_name == "int"
    assert docstring.params[1].description == "bla desc"
    assert docstring.params[2].arg_name == "yay"
    assert docstring.params[2].type_name == "str"
    assert docstring.params[2].description == ""
    assert len(docstring.raises) == 1
    assert docstring.raises[0].type_name == "ValueError"
    assert docstring.raises[0].description == "exc desc"
    assert docstring.returns is not None
    assert docstring.returns.type_name == "tuple"
    assert docstring.returns.description == "ret desc"
    assert docstring.many_returns is not None
    assert len(docstring.many_returns) == 1
    assert docstring.many_returns[0] == docstring.returns


def test_numpydoc() -> None:
    """Test numpydoc-style parser autodetection."""
    docstring = parse(
        """Short description

        Long description

        Causing people to indent:

            A lot sometimes

        Parameters
        ----------
        spam
            spam desc
        bla : int
            bla desc
        yay : str

        Raises
        ------
        ValueError
            exc desc

        Other Parameters
        ----------------
        this_guy : int, optional
            you know him

        Returns
        -------
        tuple
            ret desc

        See Also
        --------
        multiple lines...
        something else?

        Warnings
        --------
        multiple lines...
        none of this is real!
        """
    )

    assert docstring.style == DocstringStyle.NUMPYDOC
    assert docstring.short_description == "Short description"
    assert docstring.long_description == (
        "Long description\n\nCausing people to indent:\n\n    A lot sometimes"
    )
    assert len(docstring.params) == 4
    assert docstring.params[0].arg_name == "spam"
    assert docstring.params[0].type_name is None
    assert docstring.params[0].description == "spam desc"
    assert docstring.params[1].arg_name == "bla"
    assert docstring.params[1].type_name == "int"
    assert docstring.params[1].description == "bla desc"
    assert docstring.params[2].arg_name == "yay"
    assert docstring.params[2].type_name == "str"
    assert docstring.params[2].description is None
    assert docstring.params[3].arg_name == "this_guy"
    assert docstring.params[3].type_name == "int"
    assert docstring.params[3].is_optional
    assert docstring.params[3].description == "you know him"

    assert len(docstring.raises) == 1
    assert docstring.raises[0].type_name == "ValueError"
    assert docstring.raises[0].description == "exc desc"
    assert docstring.returns is not None
    assert docstring.returns.type_name == "tuple"
    assert docstring.returns.description == "ret desc"
    assert docstring.many_returns is not None
    assert len(docstring.many_returns) == 1
    assert docstring.many_returns[0] == docstring.returns


def test_autodetection_error_detection() -> None:
    """Test autodetection.

    Case where one of the parsers throws an error and another one succeeds.
    """
    source = """
    Does something useless

    :param 3 + 3 a: a param
    """

    with pytest.raises(ParseError):
        # assert that one of the parsers does raise
        parse(source, DocstringStyle.REST)

    # assert that autodetection still works
    docstring = parse(source)

    assert docstring
    assert docstring.style == DocstringStyle.GOOGLE


def test_autodetection_error() -> None:
    """Test autodetection.

    Case where all available parsers fail.
    """
    source = """
    Does something useless

    :param 3 + 3 a: a param
    """
    patched_map = {
        DocstringStyle.REST: rest,
        DocstringStyle.EPYDOC: rest,
    }
    with (
        patch("pymend.docstring_parser.base_parser._STYLE_MAP", patched_map),
        pytest.raises(ParseError),
    ):
        base_parser.parse(source)


def test_compose_empty_docstring() -> None:
    """Test what compose does when called on an empty docstring without style."""
    docstring = Docstring()
    with pytest.raises(
        ValueError,
        match=re.escape(
            "Detected docstring.style of `None` and requested style of `AUTO`."
        ),
    ):
        compose(docstring)


def test_roundtrip_mixed_numpy_google_preserves_types_and_descriptions() -> None:
    """Round-trip mixed NumPy/Google docs across styles without losing metadata."""
    source = """
    Summary line.

    Parameters
    ----------
        delta_secs (int): Number of seconds elapsed in the past.

    Returns:
    -------
        value (str): Relative-time display string.
    """
    parsed_numpy = parse(source, DocstringStyle.NUMPYDOC)
    assert parsed_numpy.params[0].arg_name == "delta_secs"
    assert parsed_numpy.params[0].type_name == "int"
    assert (
        parsed_numpy.params[0].description
        == "Number of seconds elapsed in the past."
    )
    assert parsed_numpy.returns is not None
    assert parsed_numpy.returns.return_name == "value"
    assert parsed_numpy.returns.type_name == "str"
    assert parsed_numpy.returns.description == "Relative-time display string."

    google_text = compose(parsed_numpy, style=DocstringStyle.GOOGLE)
    parsed_google = parse(google_text, DocstringStyle.GOOGLE)
    assert parsed_google.params[0].arg_name == "delta_secs"
    assert parsed_google.params[0].type_name == "int"
    assert (
        parsed_google.params[0].description
        == "Number of seconds elapsed in the past."
    )
    assert parsed_google.returns is not None
    assert parsed_google.returns.return_name == "value"
    assert parsed_google.returns.type_name == "str"
    assert parsed_google.returns.description == "Relative-time display string."

    numpy_text = compose(parsed_google, style=DocstringStyle.NUMPYDOC)
    reparsed_numpy = parse(numpy_text, DocstringStyle.NUMPYDOC)
    assert reparsed_numpy.params[0].arg_name == "delta_secs"
    assert reparsed_numpy.params[0].type_name == "int"
    assert (
        reparsed_numpy.params[0].description
        == "Number of seconds elapsed in the past."
    )
    assert reparsed_numpy.returns is not None
    assert reparsed_numpy.returns.return_name == "value"
    assert reparsed_numpy.returns.type_name == "str"
    assert reparsed_numpy.returns.description == "Relative-time display string."
