<!DOCTYPE html>
<html>
  <head>
    <meta http-equiv="content-type" content="text/html; charset=UTF-8">
    <meta name="viewport" content="width=device-width">
    <title>config</title>
    <style type="text/css">

.comment {background-color: #f2f2f2;}

.ini_block {
  text-align: left;
  background-color: #CCFFCC;
  font-size: 1.3em;
  font-weight: bold;
}

input:read-only {
  background-color: #90CAF9;
  font-size: 1.0em;
}
button {
  font-size: 1.3em;
  background-color: #2596be;
}
.ueberschrift{
    font-family:Arial;
    font-size:150%;
    color: #000000;
    }

</style>
  </head>
<body>
<!--HIERZURUECK-->

<?php

function config_lesen( $file, $readonly )
{
    $myfile = fopen($file, "r") or die("Kann Datei ".$file." nicht öffnen!");
    $Zeilencounter = 0;
    $KommentarBlock = '';
    while(!feof($myfile)) {
        $Zeile = fgets($myfile);
        $Zeile = rtrim($Zeile);

        // Kommentarzeile
        if ((strpos($Zeile, ';') !== false) && (strpos($Zeile, ';') < 2)) {
            $KommentarZeilen[] = htmlspecialchars($Zeile);
            continue;
        }

        // Falls ein Kommentarblock fertig ist, jetzt ausgeben
        if (!empty($KommentarZeilen)) {
            $block = implode('<br>', $KommentarZeilen);
            echo '<tr class="comment"><td colspan="2">'.$block.' </td></tr>'."\n";
            $Zeilencounter++;
            $KommentarZeilen = [];
        }
    
        // Rest wie gehabt...
        if ((strpos($Zeile, '[') !== false) && (strpos($Zeile, '[') < 1)) {
            echo '<tr><td class="ini_block" colspan="2"><input type="hidden" name="Zeile['.$Zeilencounter.']" value=\''.$Zeile.'\' >'.$Zeile.'</td></tr>'."\n";
        }
        elseif (strpos($Zeile, '=') !== false) {
            $Zeilenteil = explode("=", $Zeile, 2);
            $Zeilenteil[0] = trim($Zeilenteil[0]);
            $Zeilenteil[1] = trim($Zeilenteil[1]);
            echo '<tr><td class="variablenname">'.$Zeilenteil[0].'</td>'."\n";
            echo '<td><input type="text" name="Zeile['.$Zeilencounter.'][1]" value="'.htmlentities($Zeilenteil[1]).'" '.$readonly.'></td></tr>'."\n";
        } else {
            echo '<tr><td colspan="2"><input type="hidden" name="Zeile['.$Zeilencounter.']" value=\''.$Zeile.'\' >'.$Zeile.'</td></tr>'."\n";
        }

        $Zeilencounter++;
    }

    // Falls Datei mit Kommentar endet
    if (!empty($KommentarZeilen)) {
        $block = implode('<br>', $KommentarZeilen);
        echo '<tr class="comment"><td colspan="2">
                <input type="hidden" name="Zeile['.$Zeilencounter.']" value=\''.$block.'\' >'.$block.'
            </td></tr>'."\n";
    }
}

$config_ini_files = ['default.ini', 'weather.ini', 'charge.ini', 'dynprice.ini'];

# AUSGEBEN aller *.ini
include "config.php";
if(file_exists("config_priv.php")){
  include "config_priv.php";
}

foreach ($config_ini_files as $file) {
    $filename = $PythonDIR.'/CONFIG/'.$file;
    $ankor_text = "Hilfezu".str_replace(['_', '.'], '', $filename);
    echo '<br><center><a href="#'.$ankor_text.'" style="font-size: 1.7rem; text-decoration: none;">⬇</a>&nbsp;&nbsp;';
    echo '<button type="submit">Hilfe zu '.$filename.'</button>';
    echo '&nbsp;&nbsp;<a href="#top" style="font-size: 1.7rem; text-decoration: none;">⬆</a></center>';
    echo '<br><br>';
    echo '<table>';

    config_lesen($filename, 'readonly');

    echo '</table>';
    echo '<div id="'.$ankor_text.'"></div>';
}
echo '<br /><br /><hr />Hilfe erzeugt am '.date("d.m.Y", $timestamp).' durch make_config_help.php&nbsp;&nbsp;<a href="#top" style="font-size: 1.7rem; text-decoration: none;">⬆</a><br />';
?>

</body>
</html>
