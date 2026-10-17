package com.awulokune.awugokturk.ui

import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.withStyle

/**
 * Basit C++/Arduino sözdizimi renklendirmesi.
 * (Tam bir dilbilgisi değil; anahtar sözcük/yorum/metin/sayı vurgusu.)
 */
private val ANAHTAR = setOf(
    "if", "else", "for", "while", "do", "switch", "case", "default", "break", "continue",
    "return", "goto", "sizeof", "true", "false", "HIGH", "LOW", "INPUT", "OUTPUT",
    "INPUT_PULLUP", "LED_BUILTIN", "pinMode", "digitalWrite", "digitalRead", "analogRead",
    "analogWrite", "delay", "delayMicroseconds", "millis", "micros", "tone", "noTone",
    "pulseIn", "attachInterrupt", "detachInterrupt", "analogReadResolution"
)

private val TIPLER = setOf(
    "void", "int", "long", "short", "float", "double", "bool", "boolean", "byte", "char",
    "unsigned", "const", "static", "String", "uint8_t", "uint16_t", "uint32_t", "int8_t",
    "int16_t", "int32_t", "size_t", "class", "struct", "public", "private", "protected",
    "template", "namespace", "using", "volatile"
)

fun highlightCpp(src: String): AnnotatedString {
    val cAnahtar = Color(0xFF66D9C8)
    val cTip = Color(0xFF9CDCFE)
    val cSayi = Color(0xFFF2C879)
    val cMetin = Color(0xFFA9DC76)
    val cYorum = Color(0xFF708A87)
    val cOnIslem = Color(0xFFC792EA)
    val cCagri = Color(0xFFFFFFFF)
    val cDuz = Color(0xFFE6EDEB)

    return buildAnnotatedString {
        val n = src.length
        var i = 0
        while (i < n) {
            val ch = src[i]
            when {
                ch == '/' && i + 1 < n && src[i + 1] == '/' -> {
                    var j = src.indexOf('\n', i)
                    if (j < 0) j = n
                    withStyle(SpanStyle(color = cYorum)) { append(src.substring(i, j)) }
                    i = j
                }
                ch == '/' && i + 1 < n && src[i + 1] == '*' -> {
                    var j = src.indexOf("*/", i + 2)
                    j = if (j < 0) n else j + 2
                    withStyle(SpanStyle(color = cYorum)) { append(src.substring(i, j)) }
                    i = j
                }
                ch == '"' || ch == '\'' -> {
                    val quote = ch
                    var j = i + 1
                    while (j < n) {
                        val c = src[j]
                        if (c == '\\' && j + 1 < n) j += 2
                        else if (c == quote) { j++; break }
                        else j++
                    }
                    if (j > n) j = n
                    withStyle(SpanStyle(color = cMetin)) { append(src.substring(i, j)) }
                    i = j
                }
                ch == '#' -> {
                    var j = src.indexOf('\n', i)
                    if (j < 0) j = n
                    withStyle(SpanStyle(color = cOnIslem)) { append(src.substring(i, j)) }
                    i = j
                }
                ch.isLetter() || ch == '_' -> {
                    var j = i
                    while (j < n && (src[j].isLetterOrDigit() || src[j] == '_')) j++
                    val kelime = src.substring(i, j)
                    var k = j
                    while (k < n && src[k] == ' ') k++
                    val cagri = k < n && src[k] == '('
                    val renk = when {
                        ANAHTAR.contains(kelime) -> cAnahtar
                        TIPLER.contains(kelime) -> cTip
                        cagri -> cCagri
                        else -> cDuz
                    }
                    withStyle(SpanStyle(color = renk)) { append(kelime) }
                    i = j
                }
                ch.isDigit() -> {
                    var j = i
                    while (j < n && (src[j].isLetterOrDigit() || src[j] == '.' || src[j] == 'x')) j++
                    withStyle(SpanStyle(color = cSayi)) { append(src.substring(i, j)) }
                    i = j
                }
                else -> {
                    append(ch)
                    i++
                }
            }
        }
    }
}
