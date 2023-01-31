import mido

class MIDIMixer():

    def __init__(self, lowestRough:list, highesRough:list, fineAbs:list):

        availablePorts = mido.get_output_names()
        print(availablePorts)


        if 'X-Touch-Ext 1' in availablePorts:
            self.inDevice = 'X-Touch-Ext 0'
            self.outDevice = 'X-Touch-Ext 1'
        elif 'Platform X+1 V2.10 1' in availablePorts:
            self.inDevice = 'Platform X+1 V2.10 0'
            self.outDevice = 'Platform X+1 V2.10 1'

        else:
            print("Non of the compatibale MIDI devices are connected")
            exit()

        self.inport = mido.open_input(self.inDevice)
        self.outport = mido.open_output(self.outDevice)

        print(self.outport)

        self.lowestRough = lowestRough      # Lowest value of the rough tuning scale
        self.highesRough = highesRough      # Lowest value of the rough tuning scale
        self.fineAbs = fineAbs              # The fining tuning scale is [-fineAbs, fineAbs]


        # Test that the arguments are lists with 4 elements.
        try:
            self.lowestRough[3]
            self.highesRough[3]
            self.fineAbs[3]
        except:
            print("The input lists should have 4 elements.")
            exit()


        # This list has 8 elements. Each element is the pitch value of a channel.
        self.outputList = [0,0,0,0,0,0,0,0]

        # Sets the "fine-tuning" channels to the middle, i.e to "0".
        for channel in range(0,7,2):
            middle = int(round((6704-8192)/2))
            outMsg = mido.Message('pitchwheel', channel=channel, pitch = middle)
            self.outport.send(outMsg)

        self.portReading()

    def portReading(self):

        for msg in self.inport:
            parameterNumber = msg.channel // 2
            #print(msg)

            if msg.type == "pitchwheel":
                if msg.channel % 2 == 0:
                    self.fineTuning(msg, parameterNumber)

                else:
                    self.raughTuning(msg, parameterNumber)


                print(round(self.outputList[1],2), round(self.outputList[3],2), round(self.outputList[5],2), round(self.outputList[7],2), sep="\t\t")

            
            if msg.type == "note_on" and msg.velocity ==0 and msg.note % 2 == 0:
                # Resets the fine-tuning value to 0 when the fine tuning slider is released
                channel = msg.note - 104
                self.outputList[channel] = 0
                print(round(self.outputList[1],2), round(self.outputList[3],2), round(self.outputList[5],2), round(self.outputList[7],2), sep="\t\t")


            if msg.type == "note_on" and msg.channel == 0 and msg.note == 31 and msg.velocity == 127:
                #For debugging - if we press "Sel" on the right of the mixer, move all the rough-tuning sliders to the middle.
                for channel in range(1,8,2):
                    middle = int(round((6704-8192)/2))
                    outMsg = mido.Message('pitchwheel', channel=channel, pitch = middle)
                    self.outport.send(outMsg)
                    parameterNr = channel // 2
                    self.outputList[channel] = (self.highesRough[parameterNr] - self.lowestRough[parameterNr])/2
                    print(round(self.outputList[1],2), round(self.outputList[3],2), round(self.outputList[5],2), round(self.outputList[7],2), sep="\t\t")

            if msg.type == "note_on" and msg.channel == 0 and msg.note == 23 and msg.velocity == 127:
                # For debugging
                print(self.outputList)

    
    def valueMapping1(self, lowestValue: float, highestValue: float, x: float):
        # (-8192, 6704) --> (L, H)
        k = (highestValue - lowestValue)/(6704 -(-8192))        # k = Δy/𐤃x
        m = lowestValue - k*(-8192)                             # m = y - kx

        return (m + k * x)

    def valueMapping2(self, lowestValue: float, highestValue: float, x: float):
        # (L, H) --> (-8192, 6704)
        k = (6704 -(-8192))/(highestValue - lowestValue)                # k = Δy/𐤃x
        m = -8192 - k*(lowestValue)                                    # m = y - kx

        return (m + k * x)

    def raughTuning(self, msg, parameterNumber):
        # ROUGH TUNING
        # Convert the pitch into the "fine tuning" scale, and update the output list. 
        self.outputList[msg.channel] = self.valueMapping1(self.lowestRough[parameterNumber],self.highesRough[parameterNumber],msg.pitch)
        self.outport.send(msg)
        screenText = str(round(self.outputList[msg.channel],2))

        # Update the screen for the rough tuning channel
        self.updateScreen(screenText,msg.channel,1,0)


    def fineTuning(self, msg, parameterNumber):
        # Collect the current pitch value, convert it into "our" scale, and calculate the change.
        currentPitch = self.valueMapping1(-self.fineAbs[parameterNumber],self.fineAbs[parameterNumber],msg.pitch)

        
        change = currentPitch - self.outputList[msg.channel]

        # Update the output list.
        self.outputList[msg.channel] = currentPitch

        if ((self.outputList[msg.channel + 1] + change) <= self.highesRough[parameterNumber]) and ((self.outputList[msg.channel + 1] + change) >= self.lowestRough[parameterNumber]):

            # Update the "rough tuning" channel
            self.outputList[msg.channel + 1] = self.outputList[msg.channel + 1] + change

            # Convert the rough tuning pitch into "our" scale.
            newPitch = round(self.valueMapping2(self.lowestRough[parameterNumber], self.highesRough[parameterNumber], self.outputList[msg.channel + 1]))

            # Send a message to move the "rough tuning" slider.
            outMsg = mido.Message('pitchwheel', channel=msg.channel + 1, pitch = newPitch)
            self.outport.send(outMsg)

        elif (self.outputList[msg.channel + 1] + change) > self.highesRough[parameterNumber]:
            # Update the "rough tuning" channel
            self.outputList[msg.channel + 1] = self.highesRough[parameterNumber]

            # Send a message to move the "rough tuning" slider.
            outMsg = mido.Message('pitchwheel', channel=msg.channel + 1, pitch = 6704)
            self.outport.send(outMsg)

        elif (self.outputList[msg.channel + 1] + change) < self.lowestRough[parameterNumber]:
            # Update the "rough tuning" channel
            self.outputList[msg.channel + 1] = self.lowestRough[parameterNumber]

            # Send a message to move the "rough tuning" slider.
            outMsg = mido.Message('pitchwheel', channel=msg.channel + 1, pitch = -8192)
            self.outport.send(outMsg)

        # Update the screen for the fine tuning channel
        screenText = str(round(self.outputList[msg.channel],2))
        self.updateScreen(screenText,msg.channel,1,0)

        # Update the screen for the rough tuning channel
        screenText2 = str(round(self.outputList[msg.channel+1],2))
        self.updateScreen(screenText2,msg.channel+1,1,0)




    def updateScreen(self, text, screenNr, rowNr, color):
        if self.outDevice == 'X-Touch-Ext 1':   # There are no LCD displays for the other mixer.
            if len(text) <= 7: # The display cannot have more than 7 characters
                asciiText = [ord(c) for c in text]
            if len(asciiText) < 7:
                # If the text is smaller than 6 characters, fill the rest with space.
                for i in range(-len(asciiText)):
                    asciiText.append(ord(" "))
            else:
                print("The screen cannot have more than 7 letters.")
                asciiText = [ord(c) for c in "      "]


            LCDCharNumber = 7*screenNr + 8*7*rowNr      # Character number on all LCDs
            backlightColor = 0x00       # Not working

            HEADER = [0xF0, 0x00, 0x00, 0x66, 0x15, 0x12] # Constants
            msg = HEADER + [LCDCharNumber] + asciiText + [0xF7]

            # Create MIDI message from raw bytes
            message = mido.Message.from_bytes(bytes(msg))

            self.outport.send(message)

    def clearScreen(self,screenNr, RowNr):
        self.updateScreen("      ", screenNr, RowNr)






Mixer = MIDIMixer([0,0,0,0],[100,100,100,100],[5,5,5,5])

