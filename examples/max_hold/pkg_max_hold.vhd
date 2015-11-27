library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

package pkg_max_hold is

    component max_hold is
        generic (
            data_width : positive := 32
        );
        port (
            clock : in std_logic;
            reset : in std_logic;
            data  : in std_logic_vector(data_width-1 downto 0);
            max   : out std_logic_vector(data_width-1 downto 0)
        );
    end component;

end package pkg_max_hold;