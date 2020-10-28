package com.datarobot.custom

import ai.h2o.mojos.runtime.MojoPipeline;
import ai.h2o.mojos.runtime.frame.MojoFrame;
import ai.h2o.mojos.runtime.frame.MojoFrameBuilder;
import ai.h2o.mojos.runtime.frame.MojoRowBuilder;
import ai.h2o.mojos.runtime.lic.LicenseException;
import java.nio.file.{Path, Paths}
import java.io.{File, BufferedReader, FileReader, StringWriter}

import scala.util.{Try, Success, Failure}

import collection.JavaConverters._
import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVPrinter;

class H2OPredictorPipeline(name: String) extends BasePredictor(name) {

  var mojoPipeline: MojoPipeline = null
  var params: java.util.HashMap[String, Any] = null

  var isRegression: Boolean = false
  var customModelPath: String = null
  var negativeClassLabel: String = null
  var positiveClassLabel: String = null

  def configure(
      params: java.util.Map[String, Any] = new java.util.HashMap[String, Any]()
  ) = {
    mojoPipeline = loadModel(
      params.get("__custom_model_path__").asInstanceOf[String]
    )
    customModelPath = params.get("__custom_model_path__").asInstanceOf[String]
    negativeClassLabel = params.get("negativeClassLabel").asInstanceOf[String]
    positiveClassLabel = params.get("positiveClassLabel").asInstanceOf[String]

  }

  def scoreFileCSV(inputFilename: String) = {
    val csvFormat = CSVFormat.DEFAULT.withHeader();
    val parser = csvFormat.parse(
      new BufferedReader(new FileReader(new File(inputFilename)))
    )
    val sParser = parser.iterator.asScala.map { _.toMap }

    val frameBuilder = this.mojoPipeline.getInputFrameBuilder();

    sParser.map { row =>
      val rowBuilder = frameBuilder.getMojoRowBuilder();
      row.asScala.map { case (k, v) => rowBuilder.setValue(k, v) }
      frameBuilder.addRow(rowBuilder);
    }.toArray

    val iframe = frameBuilder.toMojoFrame();
    val oframe = this.mojoPipeline.transform(iframe);

    val outColumns = oframe.getColumnNames
    outColumns.zipWithIndex.map {
      case (name, index) =>
        oframe.getColumn(index).getDataAsStrings
    }.transpose
  }

  def predict(inputFilename: String): String = {
    
    val outputColumns = this.mojoPipeline.getOutputMeta.getColumnNames

    val headers = outputColumns.length match { 
      case 1 => Array("Predictions")
      case _ => outputColumns
    }
   
    val csvPrinter: CSVPrinter = new CSVPrinter(
      new StringWriter(),
      CSVFormat.DEFAULT.withHeader(headers: _*)
    )

    val predictions = Try(this.scoreFileCSV(inputFilename))

    predictions match {
      case Success(preds) =>
        preds.foreach(p =>
          csvPrinter.printRecord(p.map { _.asInstanceOf[Object] }: _*)
        )
      case Failure(e) =>
        throw new Exception(
          s"During the course of making a prediction an exception was encountered: ${e}"
        )
    }

    csvPrinter.flush()
    val outStream: StringWriter =
      csvPrinter.getOut().asInstanceOf[StringWriter];
    outStream.toString()

  }

  def loadModel(dir: String): MojoPipeline = {

    val mojoPath = Paths.get(dir, "pipeline.mojo")

    val mojoPipeline = MojoPipeline.loadFrom(mojoPath.toString)

    mojoPipeline

  }

}