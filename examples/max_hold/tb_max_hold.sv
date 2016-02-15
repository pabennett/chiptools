module tb_max_hold #(parameter data_width = 3);
    /* ------------------------------------------------------------------------
    ** data_width will be overidden by chiptools.
    ** Icarus does not support Parameter overrides, but other tools do. We work
    ** around this by providing a Parameter for tools that do support them and 
    ** then create a `define for each parameter of the same name so that tools
    ** that do not support parameter overrides can overload the `define
    ** instead. 
    ** ----------------------------------------------------------------------*/
    `ifndef data_width
        `define data_width data_width
    `endif
    /* ------------------------------------------------------------------------
    ** Registers / Wires
    ** ----------------------------------------------------------------------*/
    reg clock = 0, reset = 0;
    reg [`data_width-1:0] data;
    wire [`data_width-1:0] max;
    integer fileid;
    integer readCount;
    integer outFileId;
    integer firstCall = 1;
    integer lastCycle = 0;
    reg inReset = 0;
    reg [`data_width-1:0] inData = 0;

    /* ------------------------------------------------------------------------
    ** Open File Handles
    ** ----------------------------------------------------------------------*/
    initial begin
        fileid = $fopen("input.txt", "r");
        outFileId = $fopen("output.txt", "w");
        $display("data_width is%d", `data_width);
        if (fileid == 0) begin
            $display("Could not open file.");
            $finish;
        end
    end

    /* ------------------------------------------------------------------------
    ** Waveform File Dump 
    ** ----------------------------------------------------------------------*/
    initial begin
        $dumpfile("test.vcd");
        $dumpvars(0, tb_max_hold);
    end
    /* ------------------------------------------------------------------------
    ** Clock Generation
    ** Stimulus Generation and Logging
    ** ----------------------------------------------------------------------*/
    always begin
        #5 clock = !clock;
    end
    always begin
        if (!lastCycle) begin
            readCount = $fscanf(fileid, "%b %b\n", inReset, inData);
        end
        reset <= inReset;
        data <= inData;
        @(posedge clock);
        if (firstCall) begin
            firstCall = 0;
        end else begin
            if (!lastCycle) begin
                $fwrite(outFileId, "%b\n", max);
                if ($feof(fileid)) begin
                    $fclose(fileid);
                    lastCycle = 1;
                end
            end else begin
                $fwrite(outFileId, "%b\n", max);
                $fflush();
                $fclose(outFileId);
                $finish;
            end
        end
    end

    /* ------------------------------------------------------------------------
    ** UUT Instance
    ** ----------------------------------------------------------------------*/
    max_hold #(.data_width(`data_width)) uut (clock, reset, data, max);

endmodule
