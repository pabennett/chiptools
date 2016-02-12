module max_hold #(
   parameter data_width = 8
) (
   input clock,
   input reset,
   input [data_width-1:0] data,
   output reg [data_width-1:0] max = 0
);

always @(posedge clock) begin
    if (reset) begin
        max <= {data_width{1'b0}};
    end else if (data > max) begin
        max <= data;
    end
end
endmodule
