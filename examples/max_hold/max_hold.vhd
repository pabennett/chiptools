-------------------------------------------------------------------------------
-- max_hold.vhd
-- A simple VHDL component that continuously reads the data input and outputs
-- the maximum value until reset. Input data is interpreted as unsigned.
-------------------------------------------------------------------------------

library ieee;
    use ieee.std_logic_1164.all;
    use ieee.numeric_std.all;

entity max_hold is
    generic (
        data_width : positive := 32
    );
    port (
        clock : in std_logic;
        reset : in std_logic;
        data  : in std_logic_vector(data_width-1 downto 0);
        max   : out std_logic_vector(data_width-1 downto 0)
    );
end entity;

architecture rtl of max_hold is
    signal max_data : unsigned(data_width-1 downto 0) := (others => '0');
begin

    hold_max : procesS(clock) is
    begin
        if rising_edge(clock) then
            if reset = '1' then
                max_data <= (others => '0');
            else
                if unsigned(data) > max_data then
                    max_data <= unsigned(data);
                end if;
            end if;
        end if;
    end process;

    max <= std_logic_vector(max_data);

end rtl;