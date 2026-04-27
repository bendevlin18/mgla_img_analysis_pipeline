// ask user to select a folder
dir = getDirectory("Select A folder");
// get the list of files (& folders) in it
fileList = getFileList(dir);
// prepare a folder to output the images
output_dir = dir + File.separator + "batch_output_files" + File.separator ;
File.makeDirectory(output_dir);


//activate batch mode
setBatchMode(true);


// LOOP to process the list of files
for (i = 0; i < lengthOf(fileList); i++) {
	// define the "path" 
	// by concatenation of dir and the i element of the array fileList
	current_imagePath = dir+fileList[i];
	print(fileList[i]);
	currentImage_name = fileList[i];
	
	// basic if statement to make sure we are not including any directory folders in this loop
	// otherwise it will error out :(
	if (!File.isDirectory(current_imagePath)){

		// open the image
		// open(current_imagePath);
		print("importing image");
		run("Bio-Formats Importer", "open=" + current_imagePath + " autoscale color_mode=Grayscale rois_import=[ROI manager] view=Hyperstack stack_order=XYCZT");
		run("Z Project...", "projection=[Maximum Intensity]");
		saveAs("tiff", output_dir+currentImage_name+"_MIP");
		close("*");

}
}

//saveAs("Measurements", output_dir +"full_output.csv");
print("All Done! You can find the output here: " + output_dir);