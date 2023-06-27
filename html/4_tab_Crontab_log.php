<html>
<head>
<style>
button {
  font-size: 1.3em;
  background-color: #4CAF50;
}
@media screen and (max-width: 64em) {
body{ font-size: 160%; }
input { font-size: 100%; }
}
</style>
</head>
<body>
<a name="top" href="#bottom">Ans Ende springen!</a>
<br><br>
<?php
include "config.php";
$path_parts = pathinfo($PrognoseFile);
$file = $path_parts['dirname'].'/Crontab.log';
$myfile = fopen($file, "r") or die("Kann Datei nicht öffnen!");
$Ausgabe = 0;
$datum = date("Y-m-d", time());

$case = '';
if (isset($_POST["case"])) $case = $_POST["case"];

switch ($case) {
    case '':
    echo '<form method="POST" action="'.$_SERVER["PHP_SELF"].'">'."\n";
    echo '<input type="hidden" name="case" value="filter">'."\n";
    echo '<input type="input" name="suchstring" value="geschrieben" size="10">'."\n";
    echo '<button type="submit"> >>filtern<< </button>';
    echo '</form>'."\n";
    echo '<br>';

    # AUSGEBEN DER Crontab.log von Heute
    while(!feof($myfile)) {
        $Zeile = fgets($myfile);
        if (strpos($Zeile, $datum) !== false) $Ausgabe = 1;
        if ($Ausgabe == 1) {
            echo $Zeile . "<br>";
        }
    }
    break;

    case 'filter':
    $suchstring = '';
    if (isset($_POST["suchstring"])) $suchstring = $_POST["suchstring"];
    # Ausgabe der gesuchten Zeile mit Datumszeile 
    while(!feof($myfile)) {
        $Zeile = fgets($myfile);
        if (strpos($Zeile, $datum) !== false) $Ausgabe = 1;
        if ($Ausgabe == 1) {
            if (strpos($Zeile, 'BEGINN') !== false) {
                $BEGIN_DATE = explode(" ", $Zeile);
                $BEGIN_TIME = explode(":", $BEGIN_DATE[4]);
            }
            if (strpos($Zeile, $suchstring) !== false) {
                echo $BEGIN_TIME[0] . ":" . $BEGIN_TIME[1] . " " . $BEGIN_DATE[3] . "<br>" .  $Zeile . "<br><br>";
            }
        }
    }
    break;
}
?>

<br>
<a name="bottom" href="#top">An den Anfang springen!</a>
<br><br>
<form method="post" action="#bottom" enctype="multipart/form-data">
<button type="submit">Neu laden</button>
</form>
</body>
</html>
