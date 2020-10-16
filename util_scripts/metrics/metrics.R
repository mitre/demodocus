"
Software License Agreement (Apache 2.0)

Copyright (c) 2020, The MITRE Corporation.
All rights reserved.

Licensed under the Apache License, Version 2.0 (the 'License');
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an 'AS IS' BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

This project was developed by The MITRE Corporation.
If this code is used in a deployment or embedded within another project,
it is requested that you send an email to opensource@mitre.org in order to
let us know where this software is being used.
"

library(ggplot2)

safeColors<-c("#f7fcfd", 
"#e0ecf4", 
"#bfd3e6", 
"#9ebcda", 
"#8c96c6", 
"#8c6bb1", 
"#88419d", 
"#810f7c", 
"#4d004b")

dData <- as.matrix(read.csv("./aggregated_metrics.csv", sep=",", header=TRUE))
hData <- as.matrix(read.csv("./human_metrics.csv", sep=",", header=TRUE))

##create the set of run-times with both human and demodocus
runtime <- rbind(
			as.numeric(dData[,"total_runtime"]), 
			as.numeric(hData[,"total_runtime"])
			)
buildtime <- rbind(
			as.numeric(dData[,"build_runtime"]), 
			as.numeric(hData[,"build_runtime"])
			)

##RUNTIME output for comparison purposes
#### mean median and SD with demodocus first, then humans
mean(runtime[1,])
median(runtime[1,])
sd(runtime[1,])
#### for humans
mean(runtime[2,])
median(runtime[2,])
sd(runtime[2,])

##next task: find the delta between build_runtime and total_runtime to determine the cost of running all tests on a pre-built graph
png(filename="runtimes.png", height=500, width=500, bg="white")
boxplot(log10(t(runtime)), main="Site Evaluation Time",
	#xlab=c("Demodocus", "Human"), 
	ylab="Evaluation Time (s)", 
	col=c(safeColors[5], safeColors[9]),
	 yaxt="n", 
	 xaxt="n"
	)
	ytick<-c(2, 3, 4)
	ylabs<-c(100, 1000, 10000)
	xtick<-c(1, 2)
	xlabs<-c("Demodocus", "Human")
	axis(side=2, at=ytick, labels = ylabs)
	axis(side=1, at=xtick, labels = xlabs)
dev.off()

##find delta between num_states and num_edges for each type of user (i.e., VizKeyUser_num_states, VizMouseKeyUser_num_states, SuperVizMouseKeyUser_num_states, LowVizMouseKeyUser_num_states)
omniStates <- as.numeric(dData[,"num_states"])
humanStates <- as.numeric(hData[,"num_states"])
omniEdges <- as.numeric(dData[,"num_edges"])
humanEdges <- as.numeric(hData[,"num_edges"])
omniDStates <- as.numeric(dData[,"num_dynamic_states"])
humanDStates <- as.numeric(hData[,"num_dynamic_states"])
numMO <- rbind(as.numeric(dData[,"num_mouseover"]), as.numeric(hData[,"num_mouseover"]))
numClicks <- rbind(as.numeric(dData[,"num_clicks"]), as.numeric(hData[,"num_mouseover"]))

##GRAPH SIZE output for comparison purposes
#### mean median and SD with demodocus first, then humans
###### for graph size
mean(omniStates)
median(omniStates)
sd(omniStates)
mean(humanStates)
median(humanStates)
sd(humanStates)
###### for graph complexity (edges)
mean(omniEdges)
median(omniEdges)
sd(omniEdges)
mean(humanEdges)
median(humanEdges)
sd(humanEdges)
###### for dynamic states
mean(omniDStates)
median(omniDStates)
sd(omniDStates)
mean(humanDStates)
median(humanDStates)
sd(humanDStates)

##create graphs comparing demodocus and human graph completeness
png(filename="graphStatesSimple.png", height=500, width=500, bg="white")
barplot(rbind(omniStates, humanStates), 
	main=c("Graph Discovery Completeness:", "Demodocus vs Human"),
	xlab="Site", 
	ylab="Number of States", 
	col=c(safeColors[4], safeColors[8]),
	beside=TRUE
	)
	legend("bottomleft", 
			inset=.02,
			c("Demodocus", "Human", "Demodocus mean", "Human mean"), 
			fill=c(safeColors[5], safeColors[9]),
			bg="#ffffff"
			)
	abline(h=mean(omniStates), col=safeColors[5])
	abline(h=mean(humanStates), col=safeColors[9])
dev.off()


####my goal is to make this a geom_col plot with the bars grouped (human & demodocus) for each site but the states stacked with the number of dynamic states discovered. basically, stacked with (omniStates-omniDStates) + (omniDStates)

png(filename="graphStates.png", height=500, width=500, bg="white")

n<-length(omniStates)
statesFrame <- data.frame(
	site=c(replicate(4, dData[,1])),
	HorD=c(replicate(2*n, "demodocus"), (replicate(2*n, "human"))),
	isDynamic=c(replicate(n, "static"), replicate(n, "dynamic"), replicate(n, "static"), replicate(n, "dynamic")),
	amount=c((omniStates-omniDStates), omniDStates, (humanStates-humanDStates), humanDStates)
)

ggplot(
		data=statesFrame, 
		aes(
			x=HorD, 
			y=amount, 
			fill=(isDynamic)
			)
	) 	+ 	geom_bar(stat="identity") 	+ 	facet_grid(~site)

dev.off()


png(filename="graphEdges.png", height=500, width=500, bg="white")
barplot(rbind(omniEdges, humanEdges), 
	main=c("Graph Discovery Complexity:", "Demodocus vs Human"),
	xlab="Site", 
	ylab="Number of Edges", 
	col=c(safeColors[4], safeColors[8]),
	beside=TRUE
	)
	legend("bottomleft", 
			inset=.02,
			c("Demodocus", "Human", "Demodocus mean", "Human mean"), 
			fill=c(safeColors[5], safeColors[9]),
			bg="#ffffff"
			)
	abline(h=mean(omniEdges), col=safeColors[5])
	abline(h=mean(humanEdges), col=safeColors[9])
dev.off()

##find diffs with num_mouseover, num_clicks, etc.
png(filename="demodocusMouseClicks.png", height=500, width=500, bg="white")
barplot(numClicks[1,order(numClicks[1,])], 
	main=c("Mouse Clicks By Site:", "Demodocus"),
	xlab="Site", 
	ylab="Number of Clicks Performed", 
	col=c(safeColors[4], safeColors[8]),
	beside=FALSE
	)
	legend("bottomleft", 
			inset=.02,
			c("Demodocus", "Human", "Demodocus mean", "Human mean"), 
			fill=c(safeColors[5], safeColors[9]),
			bg="#ffffff"
			)
	abline(h=mean(omniEdges), col=safeColors[5])
	abline(h=mean(humanEdges), col=safeColors[9])
dev.off()

png(filename="HumanMouseClicks.png", height=500, width=500, bg="white")
barplot(numClicks[2,order(numClicks[1,])], 
	main=c("Mouse Clicks By Site:", "Human"),
	xlab="Site", 
	ylab="Number of Clicks Performed", 
	col=c(safeColors[4], safeColors[8]),
	beside=FALSE
	)
	legend("bottomleft", 
			inset=.02,
			c("Demodocus", "Human", "Demodocus mean", "Human mean"), 
			fill=c(safeColors[5], safeColors[9]),
			bg="#ffffff"
			)
	abline(h=mean(omniEdges), col=safeColors[5])
	abline(h=mean(humanEdges), col=safeColors[9])
dev.off()

##need to calculate average inaccessible states for each user type




##need to ID number of dead ends, i.e., paths that cause the user to not be able to go any further.









