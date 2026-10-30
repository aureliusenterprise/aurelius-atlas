# Generated from AtlasDSLParser.g4 by ANTLR 4.13.2
# encoding: utf-8
from antlr4 import *
from io import StringIO
import sys
if sys.version_info[1] > 5:
	from typing import TextIO
else:
	from typing.io import TextIO

def serializedATN():
    return [
        4,1,48,295,2,0,7,0,2,1,7,1,2,2,7,2,2,3,7,3,2,4,7,4,2,5,7,5,2,6,7,
        6,2,7,7,7,2,8,7,8,2,9,7,9,2,10,7,10,2,11,7,11,2,12,7,12,2,13,7,13,
        2,14,7,14,2,15,7,15,2,16,7,16,2,17,7,17,2,18,7,18,2,19,7,19,2,20,
        7,20,2,21,7,21,2,22,7,22,2,23,7,23,2,24,7,24,2,25,7,25,2,26,7,26,
        2,27,7,27,2,28,7,28,2,29,7,29,2,30,7,30,2,31,7,31,2,32,7,32,2,33,
        7,33,2,34,7,34,2,35,7,35,2,36,7,36,2,37,7,37,2,38,7,38,1,0,1,0,1,
        1,1,1,1,2,1,2,1,3,1,3,1,3,1,3,5,3,89,8,3,10,3,12,3,92,9,3,1,3,1,
        3,1,4,1,4,1,4,1,4,1,4,3,4,101,8,4,3,4,103,8,4,1,5,1,5,1,5,1,6,1,
        6,1,6,1,7,1,7,3,7,113,8,7,1,7,1,7,1,7,1,7,3,7,119,8,7,1,8,1,8,1,
        8,1,9,1,9,5,9,126,8,9,10,9,12,9,129,9,9,1,10,1,10,1,10,1,11,1,11,
        5,11,136,8,11,10,11,12,11,139,9,11,1,12,1,12,1,12,1,12,1,13,1,13,
        1,13,1,13,3,13,149,8,13,1,14,1,14,1,14,1,14,3,14,155,8,14,1,15,1,
        15,1,15,1,15,1,16,1,16,1,16,1,16,1,17,1,17,1,17,1,17,1,17,1,18,1,
        18,1,18,1,18,1,18,1,19,1,19,1,19,1,19,1,19,1,20,1,20,1,20,1,21,1,
        21,1,21,1,21,1,21,1,21,1,21,1,21,1,21,3,21,192,8,21,1,22,1,22,5,
        22,196,8,22,10,22,12,22,199,9,22,1,23,1,23,3,23,203,8,23,1,24,1,
        24,1,24,3,24,208,8,24,1,25,1,25,1,25,5,25,213,8,25,10,25,12,25,216,
        9,25,1,26,1,26,3,26,220,8,26,1,26,1,26,1,26,1,27,1,27,1,27,3,27,
        228,8,27,1,28,1,28,1,28,3,28,233,8,28,3,28,235,8,28,1,29,1,29,1,
        29,1,30,1,30,3,30,242,8,30,1,31,1,31,1,31,1,32,1,32,1,32,1,33,1,
        33,1,33,1,33,3,33,254,8,33,1,34,1,34,1,34,1,34,1,34,1,35,1,35,1,
        35,5,35,264,8,35,10,35,12,35,267,9,35,1,36,1,36,5,36,271,8,36,10,
        36,12,36,274,9,36,1,37,1,37,3,37,278,8,37,1,38,1,38,3,38,282,8,38,
        1,38,3,38,285,8,38,1,38,3,38,288,8,38,1,38,3,38,291,8,38,1,38,1,
        38,1,38,0,0,39,0,2,4,6,8,10,12,14,16,18,20,22,24,26,28,30,32,34,
        36,38,40,42,44,46,48,50,52,54,56,58,60,62,64,66,68,70,72,74,76,0,
        6,2,0,13,13,20,25,1,0,41,42,1,0,10,11,1,0,8,9,1,0,38,39,1,0,14,15,
        293,0,78,1,0,0,0,2,80,1,0,0,0,4,82,1,0,0,0,6,84,1,0,0,0,8,102,1,
        0,0,0,10,104,1,0,0,0,12,107,1,0,0,0,14,118,1,0,0,0,16,120,1,0,0,
        0,18,123,1,0,0,0,20,130,1,0,0,0,22,133,1,0,0,0,24,140,1,0,0,0,26,
        144,1,0,0,0,28,150,1,0,0,0,30,156,1,0,0,0,32,160,1,0,0,0,34,164,
        1,0,0,0,36,169,1,0,0,0,38,174,1,0,0,0,40,179,1,0,0,0,42,191,1,0,
        0,0,44,193,1,0,0,0,46,200,1,0,0,0,48,204,1,0,0,0,50,209,1,0,0,0,
        52,219,1,0,0,0,54,224,1,0,0,0,56,234,1,0,0,0,58,236,1,0,0,0,60,239,
        1,0,0,0,62,243,1,0,0,0,64,246,1,0,0,0,66,253,1,0,0,0,68,255,1,0,
        0,0,70,260,1,0,0,0,72,268,1,0,0,0,74,277,1,0,0,0,76,279,1,0,0,0,
        78,79,5,47,0,0,79,1,1,0,0,0,80,81,7,0,0,0,81,3,1,0,0,0,82,83,7,1,
        0,0,83,5,1,0,0,0,84,85,5,17,0,0,85,90,5,47,0,0,86,87,5,7,0,0,87,
        89,5,47,0,0,88,86,1,0,0,0,89,92,1,0,0,0,90,88,1,0,0,0,90,91,1,0,
        0,0,91,93,1,0,0,0,92,90,1,0,0,0,93,94,5,19,0,0,94,7,1,0,0,0,95,103,
        5,6,0,0,96,103,5,4,0,0,97,103,5,5,0,0,98,101,5,47,0,0,99,101,3,6,
        3,0,100,98,1,0,0,0,100,99,1,0,0,0,101,103,1,0,0,0,102,95,1,0,0,0,
        102,96,1,0,0,0,102,97,1,0,0,0,102,100,1,0,0,0,103,9,1,0,0,0,104,
        105,5,30,0,0,105,106,5,4,0,0,106,11,1,0,0,0,107,108,5,36,0,0,108,
        109,5,4,0,0,109,13,1,0,0,0,110,113,3,0,0,0,111,113,3,8,4,0,112,110,
        1,0,0,0,112,111,1,0,0,0,113,119,1,0,0,0,114,115,5,16,0,0,115,116,
        3,44,22,0,116,117,5,18,0,0,117,119,1,0,0,0,118,112,1,0,0,0,118,114,
        1,0,0,0,119,15,1,0,0,0,120,121,7,2,0,0,121,122,3,14,7,0,122,17,1,
        0,0,0,123,127,3,14,7,0,124,126,3,16,8,0,125,124,1,0,0,0,126,129,
        1,0,0,0,127,125,1,0,0,0,127,128,1,0,0,0,128,19,1,0,0,0,129,127,1,
        0,0,0,130,131,7,3,0,0,131,132,3,18,9,0,132,21,1,0,0,0,133,137,3,
        18,9,0,134,136,3,20,10,0,135,134,1,0,0,0,136,139,1,0,0,0,137,135,
        1,0,0,0,137,138,1,0,0,0,138,23,1,0,0,0,139,137,1,0,0,0,140,141,3,
        22,11,0,141,142,3,2,1,0,142,143,3,22,11,0,143,25,1,0,0,0,144,145,
        3,22,11,0,145,148,7,4,0,0,146,149,3,0,0,0,147,149,3,44,22,0,148,
        146,1,0,0,0,148,147,1,0,0,0,149,27,1,0,0,0,150,151,3,22,11,0,151,
        154,5,45,0,0,152,155,3,0,0,0,153,155,3,44,22,0,154,152,1,0,0,0,154,
        153,1,0,0,0,155,29,1,0,0,0,156,157,3,22,11,0,157,158,5,40,0,0,158,
        159,3,0,0,0,159,31,1,0,0,0,160,161,5,35,0,0,161,162,5,16,0,0,162,
        163,5,18,0,0,163,33,1,0,0,0,164,165,5,32,0,0,165,166,5,16,0,0,166,
        167,3,44,22,0,167,168,5,18,0,0,168,35,1,0,0,0,169,170,5,33,0,0,170,
        171,5,16,0,0,171,172,3,44,22,0,172,173,5,18,0,0,173,37,1,0,0,0,174,
        175,5,34,0,0,175,176,5,16,0,0,176,177,3,44,22,0,177,178,5,18,0,0,
        178,39,1,0,0,0,179,180,7,5,0,0,180,181,3,42,21,0,181,41,1,0,0,0,
        182,192,3,24,12,0,183,192,3,26,13,0,184,192,3,30,15,0,185,192,3,
        22,11,0,186,192,3,32,16,0,187,192,3,34,17,0,188,192,3,36,18,0,189,
        192,3,38,19,0,190,192,3,28,14,0,191,182,1,0,0,0,191,183,1,0,0,0,
        191,184,1,0,0,0,191,185,1,0,0,0,191,186,1,0,0,0,191,187,1,0,0,0,
        191,188,1,0,0,0,191,189,1,0,0,0,191,190,1,0,0,0,192,43,1,0,0,0,193,
        197,3,42,21,0,194,196,3,40,20,0,195,194,1,0,0,0,196,199,1,0,0,0,
        197,195,1,0,0,0,197,198,1,0,0,0,198,45,1,0,0,0,199,197,1,0,0,0,200,
        202,3,10,5,0,201,203,3,12,6,0,202,201,1,0,0,0,202,203,1,0,0,0,203,
        47,1,0,0,0,204,207,3,44,22,0,205,206,5,37,0,0,206,208,3,0,0,0,207,
        205,1,0,0,0,207,208,1,0,0,0,208,49,1,0,0,0,209,214,3,48,24,0,210,
        211,5,7,0,0,211,213,3,48,24,0,212,210,1,0,0,0,213,216,1,0,0,0,214,
        212,1,0,0,0,214,215,1,0,0,0,215,51,1,0,0,0,216,214,1,0,0,0,217,220,
        3,0,0,0,218,220,3,8,4,0,219,217,1,0,0,0,219,218,1,0,0,0,220,221,
        1,0,0,0,221,222,5,37,0,0,222,223,3,0,0,0,223,53,1,0,0,0,224,225,
        5,28,0,0,225,227,3,44,22,0,226,228,3,4,2,0,227,226,1,0,0,0,227,228,
        1,0,0,0,228,55,1,0,0,0,229,235,3,52,26,0,230,233,3,0,0,0,231,233,
        3,8,4,0,232,230,1,0,0,0,232,231,1,0,0,0,233,235,1,0,0,0,234,229,
        1,0,0,0,234,232,1,0,0,0,235,57,1,0,0,0,236,237,5,27,0,0,237,238,
        3,44,22,0,238,59,1,0,0,0,239,241,3,56,28,0,240,242,3,58,29,0,241,
        240,1,0,0,0,241,242,1,0,0,0,242,61,1,0,0,0,243,244,5,26,0,0,244,
        245,3,60,30,0,245,63,1,0,0,0,246,247,5,31,0,0,247,248,3,50,25,0,
        248,65,1,0,0,0,249,254,3,62,31,0,250,254,3,58,29,0,251,254,3,60,
        30,0,252,254,3,44,22,0,253,249,1,0,0,0,253,250,1,0,0,0,253,251,1,
        0,0,0,253,252,1,0,0,0,254,67,1,0,0,0,255,256,5,29,0,0,256,257,5,
        16,0,0,257,258,3,50,25,0,258,259,5,18,0,0,259,69,1,0,0,0,260,265,
        3,66,33,0,261,262,5,7,0,0,262,264,3,66,33,0,263,261,1,0,0,0,264,
        267,1,0,0,0,265,263,1,0,0,0,265,266,1,0,0,0,266,71,1,0,0,0,267,265,
        1,0,0,0,268,272,3,66,33,0,269,271,3,66,33,0,270,269,1,0,0,0,271,
        274,1,0,0,0,272,270,1,0,0,0,272,273,1,0,0,0,273,73,1,0,0,0,274,272,
        1,0,0,0,275,278,3,70,35,0,276,278,3,72,36,0,277,275,1,0,0,0,277,
        276,1,0,0,0,278,75,1,0,0,0,279,281,3,74,37,0,280,282,3,68,34,0,281,
        280,1,0,0,0,281,282,1,0,0,0,282,284,1,0,0,0,283,285,3,64,32,0,284,
        283,1,0,0,0,284,285,1,0,0,0,285,287,1,0,0,0,286,288,3,54,27,0,287,
        286,1,0,0,0,287,288,1,0,0,0,288,290,1,0,0,0,289,291,3,46,23,0,290,
        289,1,0,0,0,290,291,1,0,0,0,291,292,1,0,0,0,292,293,5,0,0,1,293,
        77,1,0,0,0,27,90,100,102,112,118,127,137,148,154,191,197,202,207,
        214,219,227,232,234,241,253,265,272,277,281,284,287,290
    ]

class AtlasDSLParser ( Parser ):

    grammarFileName = "AtlasDSLParser.g4"

    atn = ATNDeserializer().deserialize(serializedATN())

    decisionsToDFA = [ DFA(ds, i) for i, ds in enumerate(atn.decisionToState) ]

    sharedContextCache = PredictionContextCache()

    literalNames = [ "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                     "<INVALID>", "<INVALID>", "<INVALID>", "','", "'+'", 
                     "'-'", "'*'", "'/'", "'.'", "<INVALID>", "<INVALID>", 
                     "<INVALID>", "'('", "'['", "')'", "']'" ]

    symbolicNames = [ "<INVALID>", "SINGLE_LINE_COMMENT", "MULTILINE_COMMENT", 
                      "WS", "NUMBER", "FLOATING_NUMBER", "BOOL", "K_COMMA", 
                      "K_PLUS", "K_MINUS", "K_STAR", "K_DIV", "K_DOT", "K_LIKE", 
                      "K_AND", "K_OR", "K_LPAREN", "K_LBRACKET", "K_RPAREN", 
                      "K_RBRACKET", "K_LT", "K_LTE", "K_EQ", "K_NEQ", "K_GT", 
                      "K_GTE", "K_FROM", "K_WHERE", "K_ORDERBY", "K_GROUPBY", 
                      "K_LIMIT", "K_SELECT", "K_MAX", "K_MIN", "K_SUM", 
                      "K_COUNT", "K_OFFSET", "K_AS", "K_ISA", "K_IS", "K_HAS", 
                      "K_ASC", "K_DESC", "K_TRUE", "K_FALSE", "K_HASTERM", 
                      "KEYWORD", "ID", "STRING" ]

    RULE_identifier = 0
    RULE_operator = 1
    RULE_sortOrder = 2
    RULE_valueArray = 3
    RULE_literal = 4
    RULE_limitClause = 5
    RULE_offsetClause = 6
    RULE_atomE = 7
    RULE_multiERight = 8
    RULE_multiE = 9
    RULE_arithERight = 10
    RULE_arithE = 11
    RULE_comparisonClause = 12
    RULE_isClause = 13
    RULE_hasTermClause = 14
    RULE_hasClause = 15
    RULE_countClause = 16
    RULE_maxClause = 17
    RULE_minClause = 18
    RULE_sumClause = 19
    RULE_exprRight = 20
    RULE_compE = 21
    RULE_expr = 22
    RULE_limitOffset = 23
    RULE_selectExpression = 24
    RULE_selectExpr = 25
    RULE_aliasExpr = 26
    RULE_orderByExpr = 27
    RULE_fromSrc = 28
    RULE_whereClause = 29
    RULE_fromExpression = 30
    RULE_fromClause = 31
    RULE_selectClause = 32
    RULE_singleQrySrc = 33
    RULE_groupByExpression = 34
    RULE_commaDelimitedQueries = 35
    RULE_spaceDelimitedQueries = 36
    RULE_querySrc = 37
    RULE_query = 38

    ruleNames =  [ "identifier", "operator", "sortOrder", "valueArray", 
                   "literal", "limitClause", "offsetClause", "atomE", "multiERight", 
                   "multiE", "arithERight", "arithE", "comparisonClause", 
                   "isClause", "hasTermClause", "hasClause", "countClause", 
                   "maxClause", "minClause", "sumClause", "exprRight", "compE", 
                   "expr", "limitOffset", "selectExpression", "selectExpr", 
                   "aliasExpr", "orderByExpr", "fromSrc", "whereClause", 
                   "fromExpression", "fromClause", "selectClause", "singleQrySrc", 
                   "groupByExpression", "commaDelimitedQueries", "spaceDelimitedQueries", 
                   "querySrc", "query" ]

    EOF = Token.EOF
    SINGLE_LINE_COMMENT=1
    MULTILINE_COMMENT=2
    WS=3
    NUMBER=4
    FLOATING_NUMBER=5
    BOOL=6
    K_COMMA=7
    K_PLUS=8
    K_MINUS=9
    K_STAR=10
    K_DIV=11
    K_DOT=12
    K_LIKE=13
    K_AND=14
    K_OR=15
    K_LPAREN=16
    K_LBRACKET=17
    K_RPAREN=18
    K_RBRACKET=19
    K_LT=20
    K_LTE=21
    K_EQ=22
    K_NEQ=23
    K_GT=24
    K_GTE=25
    K_FROM=26
    K_WHERE=27
    K_ORDERBY=28
    K_GROUPBY=29
    K_LIMIT=30
    K_SELECT=31
    K_MAX=32
    K_MIN=33
    K_SUM=34
    K_COUNT=35
    K_OFFSET=36
    K_AS=37
    K_ISA=38
    K_IS=39
    K_HAS=40
    K_ASC=41
    K_DESC=42
    K_TRUE=43
    K_FALSE=44
    K_HASTERM=45
    KEYWORD=46
    ID=47
    STRING=48

    def __init__(self, input:TokenStream, output:TextIO = sys.stdout):
        super().__init__(input, output)
        self.checkVersion("4.13.2")
        self._interp = ParserATNSimulator(self, self.atn, self.decisionsToDFA, self.sharedContextCache)
        self._predicates = None




    class IdentifierContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ID(self):
            return self.getToken(AtlasDSLParser.ID, 0)

        def getRuleIndex(self):
            return AtlasDSLParser.RULE_identifier




    def identifier(self):

        localctx = AtlasDSLParser.IdentifierContext(self, self._ctx, self.state)
        self.enterRule(localctx, 0, self.RULE_identifier)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 78
            self.match(AtlasDSLParser.ID)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class OperatorContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def K_LT(self):
            return self.getToken(AtlasDSLParser.K_LT, 0)

        def K_LTE(self):
            return self.getToken(AtlasDSLParser.K_LTE, 0)

        def K_EQ(self):
            return self.getToken(AtlasDSLParser.K_EQ, 0)

        def K_NEQ(self):
            return self.getToken(AtlasDSLParser.K_NEQ, 0)

        def K_GT(self):
            return self.getToken(AtlasDSLParser.K_GT, 0)

        def K_GTE(self):
            return self.getToken(AtlasDSLParser.K_GTE, 0)

        def K_LIKE(self):
            return self.getToken(AtlasDSLParser.K_LIKE, 0)

        def getRuleIndex(self):
            return AtlasDSLParser.RULE_operator




    def operator(self):

        localctx = AtlasDSLParser.OperatorContext(self, self._ctx, self.state)
        self.enterRule(localctx, 2, self.RULE_operator)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 80
            _la = self._input.LA(1)
            if not((((_la) & ~0x3f) == 0 and ((1 << _la) & 66068480) != 0)):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class SortOrderContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def K_ASC(self):
            return self.getToken(AtlasDSLParser.K_ASC, 0)

        def K_DESC(self):
            return self.getToken(AtlasDSLParser.K_DESC, 0)

        def getRuleIndex(self):
            return AtlasDSLParser.RULE_sortOrder




    def sortOrder(self):

        localctx = AtlasDSLParser.SortOrderContext(self, self._ctx, self.state)
        self.enterRule(localctx, 4, self.RULE_sortOrder)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 82
            _la = self._input.LA(1)
            if not(_la==41 or _la==42):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ValueArrayContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def K_LBRACKET(self):
            return self.getToken(AtlasDSLParser.K_LBRACKET, 0)

        def ID(self, i:int=None):
            if i is None:
                return self.getTokens(AtlasDSLParser.ID)
            else:
                return self.getToken(AtlasDSLParser.ID, i)

        def K_RBRACKET(self):
            return self.getToken(AtlasDSLParser.K_RBRACKET, 0)

        def K_COMMA(self, i:int=None):
            if i is None:
                return self.getTokens(AtlasDSLParser.K_COMMA)
            else:
                return self.getToken(AtlasDSLParser.K_COMMA, i)

        def getRuleIndex(self):
            return AtlasDSLParser.RULE_valueArray




    def valueArray(self):

        localctx = AtlasDSLParser.ValueArrayContext(self, self._ctx, self.state)
        self.enterRule(localctx, 6, self.RULE_valueArray)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 84
            self.match(AtlasDSLParser.K_LBRACKET)
            self.state = 85
            self.match(AtlasDSLParser.ID)
            self.state = 90
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==7:
                self.state = 86
                self.match(AtlasDSLParser.K_COMMA)
                self.state = 87
                self.match(AtlasDSLParser.ID)
                self.state = 92
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 93
            self.match(AtlasDSLParser.K_RBRACKET)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class LiteralContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def BOOL(self):
            return self.getToken(AtlasDSLParser.BOOL, 0)

        def NUMBER(self):
            return self.getToken(AtlasDSLParser.NUMBER, 0)

        def FLOATING_NUMBER(self):
            return self.getToken(AtlasDSLParser.FLOATING_NUMBER, 0)

        def ID(self):
            return self.getToken(AtlasDSLParser.ID, 0)

        def valueArray(self):
            return self.getTypedRuleContext(AtlasDSLParser.ValueArrayContext,0)


        def getRuleIndex(self):
            return AtlasDSLParser.RULE_literal




    def literal(self):

        localctx = AtlasDSLParser.LiteralContext(self, self._ctx, self.state)
        self.enterRule(localctx, 8, self.RULE_literal)
        try:
            self.state = 102
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [6]:
                self.enterOuterAlt(localctx, 1)
                self.state = 95
                self.match(AtlasDSLParser.BOOL)
                pass
            elif token in [4]:
                self.enterOuterAlt(localctx, 2)
                self.state = 96
                self.match(AtlasDSLParser.NUMBER)
                pass
            elif token in [5]:
                self.enterOuterAlt(localctx, 3)
                self.state = 97
                self.match(AtlasDSLParser.FLOATING_NUMBER)
                pass
            elif token in [17, 47]:
                self.enterOuterAlt(localctx, 4)
                self.state = 100
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [47]:
                    self.state = 98
                    self.match(AtlasDSLParser.ID)
                    pass
                elif token in [17]:
                    self.state = 99
                    self.valueArray()
                    pass
                else:
                    raise NoViableAltException(self)

                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class LimitClauseContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def K_LIMIT(self):
            return self.getToken(AtlasDSLParser.K_LIMIT, 0)

        def NUMBER(self):
            return self.getToken(AtlasDSLParser.NUMBER, 0)

        def getRuleIndex(self):
            return AtlasDSLParser.RULE_limitClause




    def limitClause(self):

        localctx = AtlasDSLParser.LimitClauseContext(self, self._ctx, self.state)
        self.enterRule(localctx, 10, self.RULE_limitClause)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 104
            self.match(AtlasDSLParser.K_LIMIT)
            self.state = 105
            self.match(AtlasDSLParser.NUMBER)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class OffsetClauseContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def K_OFFSET(self):
            return self.getToken(AtlasDSLParser.K_OFFSET, 0)

        def NUMBER(self):
            return self.getToken(AtlasDSLParser.NUMBER, 0)

        def getRuleIndex(self):
            return AtlasDSLParser.RULE_offsetClause




    def offsetClause(self):

        localctx = AtlasDSLParser.OffsetClauseContext(self, self._ctx, self.state)
        self.enterRule(localctx, 12, self.RULE_offsetClause)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 107
            self.match(AtlasDSLParser.K_OFFSET)
            self.state = 108
            self.match(AtlasDSLParser.NUMBER)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class AtomEContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def identifier(self):
            return self.getTypedRuleContext(AtlasDSLParser.IdentifierContext,0)


        def literal(self):
            return self.getTypedRuleContext(AtlasDSLParser.LiteralContext,0)


        def K_LPAREN(self):
            return self.getToken(AtlasDSLParser.K_LPAREN, 0)

        def expr(self):
            return self.getTypedRuleContext(AtlasDSLParser.ExprContext,0)


        def K_RPAREN(self):
            return self.getToken(AtlasDSLParser.K_RPAREN, 0)

        def getRuleIndex(self):
            return AtlasDSLParser.RULE_atomE




    def atomE(self):

        localctx = AtlasDSLParser.AtomEContext(self, self._ctx, self.state)
        self.enterRule(localctx, 14, self.RULE_atomE)
        try:
            self.state = 118
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [4, 5, 6, 17, 47]:
                self.enterOuterAlt(localctx, 1)
                self.state = 112
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input,3,self._ctx)
                if la_ == 1:
                    self.state = 110
                    self.identifier()
                    pass

                elif la_ == 2:
                    self.state = 111
                    self.literal()
                    pass


                pass
            elif token in [16]:
                self.enterOuterAlt(localctx, 2)
                self.state = 114
                self.match(AtlasDSLParser.K_LPAREN)
                self.state = 115
                self.expr()
                self.state = 116
                self.match(AtlasDSLParser.K_RPAREN)
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class MultiERightContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def atomE(self):
            return self.getTypedRuleContext(AtlasDSLParser.AtomEContext,0)


        def K_STAR(self):
            return self.getToken(AtlasDSLParser.K_STAR, 0)

        def K_DIV(self):
            return self.getToken(AtlasDSLParser.K_DIV, 0)

        def getRuleIndex(self):
            return AtlasDSLParser.RULE_multiERight




    def multiERight(self):

        localctx = AtlasDSLParser.MultiERightContext(self, self._ctx, self.state)
        self.enterRule(localctx, 16, self.RULE_multiERight)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 120
            _la = self._input.LA(1)
            if not(_la==10 or _la==11):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
            self.state = 121
            self.atomE()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class MultiEContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def atomE(self):
            return self.getTypedRuleContext(AtlasDSLParser.AtomEContext,0)


        def multiERight(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(AtlasDSLParser.MultiERightContext)
            else:
                return self.getTypedRuleContext(AtlasDSLParser.MultiERightContext,i)


        def getRuleIndex(self):
            return AtlasDSLParser.RULE_multiE




    def multiE(self):

        localctx = AtlasDSLParser.MultiEContext(self, self._ctx, self.state)
        self.enterRule(localctx, 18, self.RULE_multiE)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 123
            self.atomE()
            self.state = 127
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==10 or _la==11:
                self.state = 124
                self.multiERight()
                self.state = 129
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ArithERightContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def multiE(self):
            return self.getTypedRuleContext(AtlasDSLParser.MultiEContext,0)


        def K_PLUS(self):
            return self.getToken(AtlasDSLParser.K_PLUS, 0)

        def K_MINUS(self):
            return self.getToken(AtlasDSLParser.K_MINUS, 0)

        def getRuleIndex(self):
            return AtlasDSLParser.RULE_arithERight




    def arithERight(self):

        localctx = AtlasDSLParser.ArithERightContext(self, self._ctx, self.state)
        self.enterRule(localctx, 20, self.RULE_arithERight)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 130
            _la = self._input.LA(1)
            if not(_la==8 or _la==9):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
            self.state = 131
            self.multiE()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ArithEContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def multiE(self):
            return self.getTypedRuleContext(AtlasDSLParser.MultiEContext,0)


        def arithERight(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(AtlasDSLParser.ArithERightContext)
            else:
                return self.getTypedRuleContext(AtlasDSLParser.ArithERightContext,i)


        def getRuleIndex(self):
            return AtlasDSLParser.RULE_arithE




    def arithE(self):

        localctx = AtlasDSLParser.ArithEContext(self, self._ctx, self.state)
        self.enterRule(localctx, 22, self.RULE_arithE)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 133
            self.multiE()
            self.state = 137
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==8 or _la==9:
                self.state = 134
                self.arithERight()
                self.state = 139
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ComparisonClauseContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def arithE(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(AtlasDSLParser.ArithEContext)
            else:
                return self.getTypedRuleContext(AtlasDSLParser.ArithEContext,i)


        def operator(self):
            return self.getTypedRuleContext(AtlasDSLParser.OperatorContext,0)


        def getRuleIndex(self):
            return AtlasDSLParser.RULE_comparisonClause




    def comparisonClause(self):

        localctx = AtlasDSLParser.ComparisonClauseContext(self, self._ctx, self.state)
        self.enterRule(localctx, 24, self.RULE_comparisonClause)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 140
            self.arithE()
            self.state = 141
            self.operator()
            self.state = 142
            self.arithE()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class IsClauseContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def arithE(self):
            return self.getTypedRuleContext(AtlasDSLParser.ArithEContext,0)


        def K_ISA(self):
            return self.getToken(AtlasDSLParser.K_ISA, 0)

        def K_IS(self):
            return self.getToken(AtlasDSLParser.K_IS, 0)

        def identifier(self):
            return self.getTypedRuleContext(AtlasDSLParser.IdentifierContext,0)


        def expr(self):
            return self.getTypedRuleContext(AtlasDSLParser.ExprContext,0)


        def getRuleIndex(self):
            return AtlasDSLParser.RULE_isClause




    def isClause(self):

        localctx = AtlasDSLParser.IsClauseContext(self, self._ctx, self.state)
        self.enterRule(localctx, 26, self.RULE_isClause)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 144
            self.arithE()
            self.state = 145
            _la = self._input.LA(1)
            if not(_la==38 or _la==39):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
            self.state = 148
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,7,self._ctx)
            if la_ == 1:
                self.state = 146
                self.identifier()
                pass

            elif la_ == 2:
                self.state = 147
                self.expr()
                pass


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class HasTermClauseContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def arithE(self):
            return self.getTypedRuleContext(AtlasDSLParser.ArithEContext,0)


        def K_HASTERM(self):
            return self.getToken(AtlasDSLParser.K_HASTERM, 0)

        def identifier(self):
            return self.getTypedRuleContext(AtlasDSLParser.IdentifierContext,0)


        def expr(self):
            return self.getTypedRuleContext(AtlasDSLParser.ExprContext,0)


        def getRuleIndex(self):
            return AtlasDSLParser.RULE_hasTermClause




    def hasTermClause(self):

        localctx = AtlasDSLParser.HasTermClauseContext(self, self._ctx, self.state)
        self.enterRule(localctx, 28, self.RULE_hasTermClause)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 150
            self.arithE()
            self.state = 151
            self.match(AtlasDSLParser.K_HASTERM)
            self.state = 154
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,8,self._ctx)
            if la_ == 1:
                self.state = 152
                self.identifier()
                pass

            elif la_ == 2:
                self.state = 153
                self.expr()
                pass


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class HasClauseContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def arithE(self):
            return self.getTypedRuleContext(AtlasDSLParser.ArithEContext,0)


        def K_HAS(self):
            return self.getToken(AtlasDSLParser.K_HAS, 0)

        def identifier(self):
            return self.getTypedRuleContext(AtlasDSLParser.IdentifierContext,0)


        def getRuleIndex(self):
            return AtlasDSLParser.RULE_hasClause




    def hasClause(self):

        localctx = AtlasDSLParser.HasClauseContext(self, self._ctx, self.state)
        self.enterRule(localctx, 30, self.RULE_hasClause)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 156
            self.arithE()
            self.state = 157
            self.match(AtlasDSLParser.K_HAS)
            self.state = 158
            self.identifier()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class CountClauseContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def K_COUNT(self):
            return self.getToken(AtlasDSLParser.K_COUNT, 0)

        def K_LPAREN(self):
            return self.getToken(AtlasDSLParser.K_LPAREN, 0)

        def K_RPAREN(self):
            return self.getToken(AtlasDSLParser.K_RPAREN, 0)

        def getRuleIndex(self):
            return AtlasDSLParser.RULE_countClause




    def countClause(self):

        localctx = AtlasDSLParser.CountClauseContext(self, self._ctx, self.state)
        self.enterRule(localctx, 32, self.RULE_countClause)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 160
            self.match(AtlasDSLParser.K_COUNT)
            self.state = 161
            self.match(AtlasDSLParser.K_LPAREN)
            self.state = 162
            self.match(AtlasDSLParser.K_RPAREN)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class MaxClauseContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def K_MAX(self):
            return self.getToken(AtlasDSLParser.K_MAX, 0)

        def K_LPAREN(self):
            return self.getToken(AtlasDSLParser.K_LPAREN, 0)

        def expr(self):
            return self.getTypedRuleContext(AtlasDSLParser.ExprContext,0)


        def K_RPAREN(self):
            return self.getToken(AtlasDSLParser.K_RPAREN, 0)

        def getRuleIndex(self):
            return AtlasDSLParser.RULE_maxClause




    def maxClause(self):

        localctx = AtlasDSLParser.MaxClauseContext(self, self._ctx, self.state)
        self.enterRule(localctx, 34, self.RULE_maxClause)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 164
            self.match(AtlasDSLParser.K_MAX)
            self.state = 165
            self.match(AtlasDSLParser.K_LPAREN)
            self.state = 166
            self.expr()
            self.state = 167
            self.match(AtlasDSLParser.K_RPAREN)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class MinClauseContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def K_MIN(self):
            return self.getToken(AtlasDSLParser.K_MIN, 0)

        def K_LPAREN(self):
            return self.getToken(AtlasDSLParser.K_LPAREN, 0)

        def expr(self):
            return self.getTypedRuleContext(AtlasDSLParser.ExprContext,0)


        def K_RPAREN(self):
            return self.getToken(AtlasDSLParser.K_RPAREN, 0)

        def getRuleIndex(self):
            return AtlasDSLParser.RULE_minClause




    def minClause(self):

        localctx = AtlasDSLParser.MinClauseContext(self, self._ctx, self.state)
        self.enterRule(localctx, 36, self.RULE_minClause)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 169
            self.match(AtlasDSLParser.K_MIN)
            self.state = 170
            self.match(AtlasDSLParser.K_LPAREN)
            self.state = 171
            self.expr()
            self.state = 172
            self.match(AtlasDSLParser.K_RPAREN)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class SumClauseContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def K_SUM(self):
            return self.getToken(AtlasDSLParser.K_SUM, 0)

        def K_LPAREN(self):
            return self.getToken(AtlasDSLParser.K_LPAREN, 0)

        def expr(self):
            return self.getTypedRuleContext(AtlasDSLParser.ExprContext,0)


        def K_RPAREN(self):
            return self.getToken(AtlasDSLParser.K_RPAREN, 0)

        def getRuleIndex(self):
            return AtlasDSLParser.RULE_sumClause




    def sumClause(self):

        localctx = AtlasDSLParser.SumClauseContext(self, self._ctx, self.state)
        self.enterRule(localctx, 38, self.RULE_sumClause)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 174
            self.match(AtlasDSLParser.K_SUM)
            self.state = 175
            self.match(AtlasDSLParser.K_LPAREN)
            self.state = 176
            self.expr()
            self.state = 177
            self.match(AtlasDSLParser.K_RPAREN)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ExprRightContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def compE(self):
            return self.getTypedRuleContext(AtlasDSLParser.CompEContext,0)


        def K_AND(self):
            return self.getToken(AtlasDSLParser.K_AND, 0)

        def K_OR(self):
            return self.getToken(AtlasDSLParser.K_OR, 0)

        def getRuleIndex(self):
            return AtlasDSLParser.RULE_exprRight




    def exprRight(self):

        localctx = AtlasDSLParser.ExprRightContext(self, self._ctx, self.state)
        self.enterRule(localctx, 40, self.RULE_exprRight)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 179
            _la = self._input.LA(1)
            if not(_la==14 or _la==15):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
            self.state = 180
            self.compE()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class CompEContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def comparisonClause(self):
            return self.getTypedRuleContext(AtlasDSLParser.ComparisonClauseContext,0)


        def isClause(self):
            return self.getTypedRuleContext(AtlasDSLParser.IsClauseContext,0)


        def hasClause(self):
            return self.getTypedRuleContext(AtlasDSLParser.HasClauseContext,0)


        def arithE(self):
            return self.getTypedRuleContext(AtlasDSLParser.ArithEContext,0)


        def countClause(self):
            return self.getTypedRuleContext(AtlasDSLParser.CountClauseContext,0)


        def maxClause(self):
            return self.getTypedRuleContext(AtlasDSLParser.MaxClauseContext,0)


        def minClause(self):
            return self.getTypedRuleContext(AtlasDSLParser.MinClauseContext,0)


        def sumClause(self):
            return self.getTypedRuleContext(AtlasDSLParser.SumClauseContext,0)


        def hasTermClause(self):
            return self.getTypedRuleContext(AtlasDSLParser.HasTermClauseContext,0)


        def getRuleIndex(self):
            return AtlasDSLParser.RULE_compE




    def compE(self):

        localctx = AtlasDSLParser.CompEContext(self, self._ctx, self.state)
        self.enterRule(localctx, 42, self.RULE_compE)
        try:
            self.state = 191
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,9,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 182
                self.comparisonClause()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 183
                self.isClause()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 184
                self.hasClause()
                pass

            elif la_ == 4:
                self.enterOuterAlt(localctx, 4)
                self.state = 185
                self.arithE()
                pass

            elif la_ == 5:
                self.enterOuterAlt(localctx, 5)
                self.state = 186
                self.countClause()
                pass

            elif la_ == 6:
                self.enterOuterAlt(localctx, 6)
                self.state = 187
                self.maxClause()
                pass

            elif la_ == 7:
                self.enterOuterAlt(localctx, 7)
                self.state = 188
                self.minClause()
                pass

            elif la_ == 8:
                self.enterOuterAlt(localctx, 8)
                self.state = 189
                self.sumClause()
                pass

            elif la_ == 9:
                self.enterOuterAlt(localctx, 9)
                self.state = 190
                self.hasTermClause()
                pass


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ExprContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def compE(self):
            return self.getTypedRuleContext(AtlasDSLParser.CompEContext,0)


        def exprRight(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(AtlasDSLParser.ExprRightContext)
            else:
                return self.getTypedRuleContext(AtlasDSLParser.ExprRightContext,i)


        def getRuleIndex(self):
            return AtlasDSLParser.RULE_expr




    def expr(self):

        localctx = AtlasDSLParser.ExprContext(self, self._ctx, self.state)
        self.enterRule(localctx, 44, self.RULE_expr)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 193
            self.compE()
            self.state = 197
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,10,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    self.state = 194
                    self.exprRight() 
                self.state = 199
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,10,self._ctx)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class LimitOffsetContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def limitClause(self):
            return self.getTypedRuleContext(AtlasDSLParser.LimitClauseContext,0)


        def offsetClause(self):
            return self.getTypedRuleContext(AtlasDSLParser.OffsetClauseContext,0)


        def getRuleIndex(self):
            return AtlasDSLParser.RULE_limitOffset




    def limitOffset(self):

        localctx = AtlasDSLParser.LimitOffsetContext(self, self._ctx, self.state)
        self.enterRule(localctx, 46, self.RULE_limitOffset)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 200
            self.limitClause()
            self.state = 202
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==36:
                self.state = 201
                self.offsetClause()


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class SelectExpressionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def expr(self):
            return self.getTypedRuleContext(AtlasDSLParser.ExprContext,0)


        def K_AS(self):
            return self.getToken(AtlasDSLParser.K_AS, 0)

        def identifier(self):
            return self.getTypedRuleContext(AtlasDSLParser.IdentifierContext,0)


        def getRuleIndex(self):
            return AtlasDSLParser.RULE_selectExpression




    def selectExpression(self):

        localctx = AtlasDSLParser.SelectExpressionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 48, self.RULE_selectExpression)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 204
            self.expr()
            self.state = 207
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==37:
                self.state = 205
                self.match(AtlasDSLParser.K_AS)
                self.state = 206
                self.identifier()


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class SelectExprContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def selectExpression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(AtlasDSLParser.SelectExpressionContext)
            else:
                return self.getTypedRuleContext(AtlasDSLParser.SelectExpressionContext,i)


        def K_COMMA(self, i:int=None):
            if i is None:
                return self.getTokens(AtlasDSLParser.K_COMMA)
            else:
                return self.getToken(AtlasDSLParser.K_COMMA, i)

        def getRuleIndex(self):
            return AtlasDSLParser.RULE_selectExpr




    def selectExpr(self):

        localctx = AtlasDSLParser.SelectExprContext(self, self._ctx, self.state)
        self.enterRule(localctx, 50, self.RULE_selectExpr)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 209
            self.selectExpression()
            self.state = 214
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==7:
                self.state = 210
                self.match(AtlasDSLParser.K_COMMA)
                self.state = 211
                self.selectExpression()
                self.state = 216
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class AliasExprContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def K_AS(self):
            return self.getToken(AtlasDSLParser.K_AS, 0)

        def identifier(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(AtlasDSLParser.IdentifierContext)
            else:
                return self.getTypedRuleContext(AtlasDSLParser.IdentifierContext,i)


        def literal(self):
            return self.getTypedRuleContext(AtlasDSLParser.LiteralContext,0)


        def getRuleIndex(self):
            return AtlasDSLParser.RULE_aliasExpr




    def aliasExpr(self):

        localctx = AtlasDSLParser.AliasExprContext(self, self._ctx, self.state)
        self.enterRule(localctx, 52, self.RULE_aliasExpr)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 219
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,14,self._ctx)
            if la_ == 1:
                self.state = 217
                self.identifier()
                pass

            elif la_ == 2:
                self.state = 218
                self.literal()
                pass


            self.state = 221
            self.match(AtlasDSLParser.K_AS)
            self.state = 222
            self.identifier()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class OrderByExprContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def K_ORDERBY(self):
            return self.getToken(AtlasDSLParser.K_ORDERBY, 0)

        def expr(self):
            return self.getTypedRuleContext(AtlasDSLParser.ExprContext,0)


        def sortOrder(self):
            return self.getTypedRuleContext(AtlasDSLParser.SortOrderContext,0)


        def getRuleIndex(self):
            return AtlasDSLParser.RULE_orderByExpr




    def orderByExpr(self):

        localctx = AtlasDSLParser.OrderByExprContext(self, self._ctx, self.state)
        self.enterRule(localctx, 54, self.RULE_orderByExpr)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 224
            self.match(AtlasDSLParser.K_ORDERBY)
            self.state = 225
            self.expr()
            self.state = 227
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==41 or _la==42:
                self.state = 226
                self.sortOrder()


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class FromSrcContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def aliasExpr(self):
            return self.getTypedRuleContext(AtlasDSLParser.AliasExprContext,0)


        def identifier(self):
            return self.getTypedRuleContext(AtlasDSLParser.IdentifierContext,0)


        def literal(self):
            return self.getTypedRuleContext(AtlasDSLParser.LiteralContext,0)


        def getRuleIndex(self):
            return AtlasDSLParser.RULE_fromSrc




    def fromSrc(self):

        localctx = AtlasDSLParser.FromSrcContext(self, self._ctx, self.state)
        self.enterRule(localctx, 56, self.RULE_fromSrc)
        try:
            self.state = 234
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,17,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 229
                self.aliasExpr()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 232
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input,16,self._ctx)
                if la_ == 1:
                    self.state = 230
                    self.identifier()
                    pass

                elif la_ == 2:
                    self.state = 231
                    self.literal()
                    pass


                pass


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class WhereClauseContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def K_WHERE(self):
            return self.getToken(AtlasDSLParser.K_WHERE, 0)

        def expr(self):
            return self.getTypedRuleContext(AtlasDSLParser.ExprContext,0)


        def getRuleIndex(self):
            return AtlasDSLParser.RULE_whereClause




    def whereClause(self):

        localctx = AtlasDSLParser.WhereClauseContext(self, self._ctx, self.state)
        self.enterRule(localctx, 58, self.RULE_whereClause)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 236
            self.match(AtlasDSLParser.K_WHERE)
            self.state = 237
            self.expr()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class FromExpressionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def fromSrc(self):
            return self.getTypedRuleContext(AtlasDSLParser.FromSrcContext,0)


        def whereClause(self):
            return self.getTypedRuleContext(AtlasDSLParser.WhereClauseContext,0)


        def getRuleIndex(self):
            return AtlasDSLParser.RULE_fromExpression




    def fromExpression(self):

        localctx = AtlasDSLParser.FromExpressionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 60, self.RULE_fromExpression)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 239
            self.fromSrc()
            self.state = 241
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,18,self._ctx)
            if la_ == 1:
                self.state = 240
                self.whereClause()


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class FromClauseContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def K_FROM(self):
            return self.getToken(AtlasDSLParser.K_FROM, 0)

        def fromExpression(self):
            return self.getTypedRuleContext(AtlasDSLParser.FromExpressionContext,0)


        def getRuleIndex(self):
            return AtlasDSLParser.RULE_fromClause




    def fromClause(self):

        localctx = AtlasDSLParser.FromClauseContext(self, self._ctx, self.state)
        self.enterRule(localctx, 62, self.RULE_fromClause)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 243
            self.match(AtlasDSLParser.K_FROM)
            self.state = 244
            self.fromExpression()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class SelectClauseContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def K_SELECT(self):
            return self.getToken(AtlasDSLParser.K_SELECT, 0)

        def selectExpr(self):
            return self.getTypedRuleContext(AtlasDSLParser.SelectExprContext,0)


        def getRuleIndex(self):
            return AtlasDSLParser.RULE_selectClause




    def selectClause(self):

        localctx = AtlasDSLParser.SelectClauseContext(self, self._ctx, self.state)
        self.enterRule(localctx, 64, self.RULE_selectClause)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 246
            self.match(AtlasDSLParser.K_SELECT)
            self.state = 247
            self.selectExpr()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class SingleQrySrcContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def fromClause(self):
            return self.getTypedRuleContext(AtlasDSLParser.FromClauseContext,0)


        def whereClause(self):
            return self.getTypedRuleContext(AtlasDSLParser.WhereClauseContext,0)


        def fromExpression(self):
            return self.getTypedRuleContext(AtlasDSLParser.FromExpressionContext,0)


        def expr(self):
            return self.getTypedRuleContext(AtlasDSLParser.ExprContext,0)


        def getRuleIndex(self):
            return AtlasDSLParser.RULE_singleQrySrc




    def singleQrySrc(self):

        localctx = AtlasDSLParser.SingleQrySrcContext(self, self._ctx, self.state)
        self.enterRule(localctx, 66, self.RULE_singleQrySrc)
        try:
            self.state = 253
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,19,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 249
                self.fromClause()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 250
                self.whereClause()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 251
                self.fromExpression()
                pass

            elif la_ == 4:
                self.enterOuterAlt(localctx, 4)
                self.state = 252
                self.expr()
                pass


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class GroupByExpressionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def K_GROUPBY(self):
            return self.getToken(AtlasDSLParser.K_GROUPBY, 0)

        def K_LPAREN(self):
            return self.getToken(AtlasDSLParser.K_LPAREN, 0)

        def selectExpr(self):
            return self.getTypedRuleContext(AtlasDSLParser.SelectExprContext,0)


        def K_RPAREN(self):
            return self.getToken(AtlasDSLParser.K_RPAREN, 0)

        def getRuleIndex(self):
            return AtlasDSLParser.RULE_groupByExpression




    def groupByExpression(self):

        localctx = AtlasDSLParser.GroupByExpressionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 68, self.RULE_groupByExpression)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 255
            self.match(AtlasDSLParser.K_GROUPBY)
            self.state = 256
            self.match(AtlasDSLParser.K_LPAREN)
            self.state = 257
            self.selectExpr()
            self.state = 258
            self.match(AtlasDSLParser.K_RPAREN)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class CommaDelimitedQueriesContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def singleQrySrc(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(AtlasDSLParser.SingleQrySrcContext)
            else:
                return self.getTypedRuleContext(AtlasDSLParser.SingleQrySrcContext,i)


        def K_COMMA(self, i:int=None):
            if i is None:
                return self.getTokens(AtlasDSLParser.K_COMMA)
            else:
                return self.getToken(AtlasDSLParser.K_COMMA, i)

        def getRuleIndex(self):
            return AtlasDSLParser.RULE_commaDelimitedQueries




    def commaDelimitedQueries(self):

        localctx = AtlasDSLParser.CommaDelimitedQueriesContext(self, self._ctx, self.state)
        self.enterRule(localctx, 70, self.RULE_commaDelimitedQueries)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 260
            self.singleQrySrc()
            self.state = 265
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==7:
                self.state = 261
                self.match(AtlasDSLParser.K_COMMA)
                self.state = 262
                self.singleQrySrc()
                self.state = 267
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class SpaceDelimitedQueriesContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def singleQrySrc(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(AtlasDSLParser.SingleQrySrcContext)
            else:
                return self.getTypedRuleContext(AtlasDSLParser.SingleQrySrcContext,i)


        def getRuleIndex(self):
            return AtlasDSLParser.RULE_spaceDelimitedQueries




    def spaceDelimitedQueries(self):

        localctx = AtlasDSLParser.SpaceDelimitedQueriesContext(self, self._ctx, self.state)
        self.enterRule(localctx, 72, self.RULE_spaceDelimitedQueries)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 268
            self.singleQrySrc()
            self.state = 272
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while (((_la) & ~0x3f) == 0 and ((1 << _la) & 140802114388080) != 0):
                self.state = 269
                self.singleQrySrc()
                self.state = 274
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class QuerySrcContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def commaDelimitedQueries(self):
            return self.getTypedRuleContext(AtlasDSLParser.CommaDelimitedQueriesContext,0)


        def spaceDelimitedQueries(self):
            return self.getTypedRuleContext(AtlasDSLParser.SpaceDelimitedQueriesContext,0)


        def getRuleIndex(self):
            return AtlasDSLParser.RULE_querySrc




    def querySrc(self):

        localctx = AtlasDSLParser.QuerySrcContext(self, self._ctx, self.state)
        self.enterRule(localctx, 74, self.RULE_querySrc)
        try:
            self.state = 277
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,22,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 275
                self.commaDelimitedQueries()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 276
                self.spaceDelimitedQueries()
                pass


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class QueryContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def querySrc(self):
            return self.getTypedRuleContext(AtlasDSLParser.QuerySrcContext,0)


        def EOF(self):
            return self.getToken(AtlasDSLParser.EOF, 0)

        def groupByExpression(self):
            return self.getTypedRuleContext(AtlasDSLParser.GroupByExpressionContext,0)


        def selectClause(self):
            return self.getTypedRuleContext(AtlasDSLParser.SelectClauseContext,0)


        def orderByExpr(self):
            return self.getTypedRuleContext(AtlasDSLParser.OrderByExprContext,0)


        def limitOffset(self):
            return self.getTypedRuleContext(AtlasDSLParser.LimitOffsetContext,0)


        def getRuleIndex(self):
            return AtlasDSLParser.RULE_query




    def query(self):

        localctx = AtlasDSLParser.QueryContext(self, self._ctx, self.state)
        self.enterRule(localctx, 76, self.RULE_query)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 279
            self.querySrc()
            self.state = 281
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==29:
                self.state = 280
                self.groupByExpression()


            self.state = 284
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==31:
                self.state = 283
                self.selectClause()


            self.state = 287
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==28:
                self.state = 286
                self.orderByExpr()


            self.state = 290
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==30:
                self.state = 289
                self.limitOffset()


            self.state = 292
            self.match(AtlasDSLParser.EOF)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx





